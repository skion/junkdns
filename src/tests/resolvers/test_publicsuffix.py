from __future__ import absolute_import

import unittest
import dns.message
from textwrap import dedent
import resolvers.publicsuffix



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


