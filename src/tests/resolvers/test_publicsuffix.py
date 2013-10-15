from __future__ import absolute_import

import unittest
import dns.opcode
import dns.message
from textwrap import dedent
import resolvers.publicsuffix
import argparse


class PublicSuffixTest(unittest.TestCase):

    def setUp(self):
        pass


    def query(self, q, a=None):
        # dnspython tokenizer is pretty picky about leading white space
        q = dedent(q).strip()
        mq = dns.message.from_text(q)
        mr = resolvers.publicsuffix.query(mq)

        if a:
            a = dedent(a).strip()
            ma = dns.message.from_text(a)
            try:
                self.assertEqual(mr, ma)
            except AssertionError:
                print("\nQuestion:")
                print(q)
                print("\nExpected:")
                print(ma)
                print("\nResult:")
                print(mr)
                raise

        return mr


    def test_configure_parser(self):
        """
        Test if argparse stuff works.
        """
        parser = argparse.ArgumentParser()
        parser = resolvers.publicsuffix.configure_parser(parser)

        url = "http://foo.bar.invalid/"

        # default args
        args = parser.parse_args([])
        args.func(args)
        self.assertNotEqual(resolvers.publicsuffix.LIST_URL, url)

        args = parser.parse_args(["--fetch", url])
        args.func(args)
        self.assertEqual(resolvers.publicsuffix.LIST_URL, url)


    def test_publicsuffix_fail(self):
        """
        Test if exception in publicsuffix gives SERVFAIL.
        """

        class MyException(Exception):
            pass
        
        def stub(name):
            raise MyException("Test")

        old = resolvers.publicsuffix.psl.get_public_suffix

        try:
            # easy way to fake an exception
            resolvers.publicsuffix.psl.get_public_suffix = stub

            q = """
                id 101
                opcode QUERY
                flags RD RA
                ;QUESTION
                test.com. IN PTR
                """
            a = """
                id 101
                opcode QUERY
                rcode SERVFAIL
                flags QR RD
                ;QUESTION
                test.com. IN PTR
                """

            self.query(q, a)

        finally:
            resolvers.publicsuffix.psl.get_public_suffix = old


    def test_validation_rd(self):
        """
        For interoperability with clients, resolver should not refuse RD bit.
        """
        q = """
            id 101
            opcode QUERY
            flags RD RA
            ;QUESTION
            test.com. IN PTR
            """
        a = """
            id 101
            opcode QUERY
            rcode NOERROR
            flags QR RD
            ;QUESTION
            test.com. IN PTR
            ;ANSWER
            test.com. 14400 IN PTR test.com.
            """
        self.query(q, a)


    def test_validation_bad_opcode(self):
        """
        Give exception when invalid opcode is given.
        """
        q = """
            id 101
            opcode BEEF
            flags RD RA
            ;QUESTION
            test.com. IN PTR
            """
        self.assertRaises(dns.opcode.UnknownOpcode, self.query, q)


    def test_validation_no_query(self):
        """
        Give error when non-QUERY opcode is given.
        """
        q = """
            id 101
            opcode UPDATE
            flags RD RA
            ;QUESTION
            test.com. IN PTR
            """
        a = """
            id 101
            opcode UPDATE
            rcode NOTIMP
            flags QR RD
            ;QUESTION
            test.com. IN PTR
            """
        self.query(q, a)


    def test_validation_multi_question(self):
        """
        Give error when multiple questions are asked.
        """
        q = """
            id 101
            opcode QUERY
            flags RD RA
            ;QUESTION
            test1.com. IN PTR
            test2.com. IN PTR
            """
        a = """
            id 101
            opcode QUERY
            rcode FORMERR
            flags QR RD
            ;QUESTION
            test1.com. IN PTR
            test2.com. IN PTR
            """
        self.query(q, a)


    def test_config_notxt(self):
        """
        Test if SERVE_TXT works.
        """
        old, resolvers.publicsuffix.SERVE_TXT = \
            resolvers.publicsuffix.SERVE_TXT, False
        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            test.com. IN PTR
            """
        r = self.query(q)
        self.assertEqual(len(r.additional), 0)
        resolvers.publicsuffix.SERVE_TXT = old


    def test_config_ttl(self):
        """
        Test if TTL config works.
        """
        old, resolvers.publicsuffix.TTL = resolvers.publicsuffix.TTL, 6633
        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            test.com. IN PTR
            """
        r = self.query(q)
        self.assertEqual(r.answer[0].ttl, 6633)
        resolvers.publicsuffix.TTL = old


    def test_query_any_ptr(self):
        """
        Query for PTR or ANY should give NOERROR.
        """
        q = """
            id 101
            opcode QUERY
            flags RA
            ;QUESTION
            test.com. IN PTR
            """
        a = """
            id 101
            opcode QUERY
            rcode NOERROR
            flags QR
            ;QUESTION
            test.com. IN PTR
            ;ANSWER
            test.com. 14400 IN PTR test.com.
            """
        self.query(q, a)

        q = """
            id 101
            opcode QUERY
            flags RA
            ;QUESTION
            test.com. IN ANY
            """
        a = """
            id 101
            opcode QUERY
            rcode NOERROR
            flags QR
            ;QUESTION
            test.com. IN ANY
            ;ANSWER
            test.com. 14400 IN PTR test.com.
            """
        self.query(q, a)


    def test_query_non_any_ptr(self):
        """
        Query for anything other than PTR or ANY should give NXDOMAIN.
        """
        q = """
            id 101
            opcode QUERY
            flags RA
            ;QUESTION
            test.com. IN A
            """
        a = """
            id 101
            opcode QUERY
            rcode NXDOMAIN
            flags QR
            ;QUESTION
            test.com. IN A
            """
        self.query(q, a)

        q = """
            id 101
            opcode QUERY
            flags RA
            ;QUESTION
            test.com. IN CNAME
            """
        a = """
            id 101
            opcode QUERY
            rcode NXDOMAIN
            flags QR
            ;QUESTION
            test.com. IN CNAME
            """
        self.query(q, a)


    def test_query_nl(self):
        """
        Test question .nl domain. 
        """

        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            test.nl. IN PTR
            """
        a = """
            id 102
            opcode QUERY
            rcode NOERROR
            flags QR 
            ;QUESTION
            test.nl. IN PTR
            ;ANSWER
            test.nl. 14400 IN PTR test.nl.
            """
        self.query(q, a)

        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            foo.test.nl. IN PTR
            """
        a = """
            id 102
            opcode QUERY
            rcode NOERROR
            flags QR 
            ;QUESTION
            foo.test.nl. IN PTR
            ;ANSWER
            foo.test.nl. 14400 IN PTR test.nl.
            """
        self.query(q, a)

        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            bar.foo.test.nl. IN PTR
            """
        a = """
            id 102
            opcode QUERY
            rcode NOERROR
            flags QR 
            ;QUESTION
            bar.foo.test.nl. IN PTR
            ;ANSWER
            bar.foo.test.nl. 14400 IN PTR test.nl.
            """
        self.query(q, a)


    def test_query_co_uk(self):
        """
        Test question .co.uk domain. 
        """

        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            test.co.uk. IN PTR
            """
        a = """
            id 102
            opcode QUERY
            rcode NOERROR
            flags QR 
            ;QUESTION
            test.co.uk. IN PTR
            ;ANSWER
            test.co.uk. 14400 IN PTR test.co.uk.
            """
        self.query(q, a)

        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            foo.test.co.uk. IN PTR
            """
        a = """
            id 102
            opcode QUERY
            rcode NOERROR
            flags QR 
            ;QUESTION
            foo.test.co.uk. IN PTR
            ;ANSWER
            foo.test.co.uk. 14400 IN PTR test.co.uk.
            """
        self.query(q, a)

        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            bar.foo.test.co.uk. IN PTR
            """
        a = """
            id 102
            opcode QUERY
            rcode NOERROR
            flags QR 
            ;QUESTION
            bar.foo.test.co.uk. IN PTR
            ;ANSWER
            bar.foo.test.co.uk. 14400 IN PTR test.co.uk.
            """
        self.query(q, a)


    def test_query_idna(self):
        """
        Test question international domain.
        """

        q = """
            id 102
            opcode QUERY
            flags RA
            ;QUESTION
            test.co.uk. IN PTR
            """
        a = """
            id 102
            opcode QUERY
            rcode NOERROR
            flags QR 
            ;QUESTION
            test.co.uk. IN PTR
            ;ANSWER
            test.co.uk. 14400 IN PTR test.co.uk.
            """
        self.query(q, a)

