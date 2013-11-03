# -:- coding: utf-8 -:-#
"""
A resolver to query top-level domains via publicsuffix.org.
"""
from __future__ import absolute_import

NAME = "publicsuffix"
HELP = "a resolver to query top-level domains via publicsuffix.org"
DESC = """
This resolver returns a PTR record pointing to the top-level domain of the 
hostname in question. When the --txt option is given, it will also return
additional informational TXT records.

The list of current top-level domains can be explicitly downloaded upon startup
via the --fetch argument.
"""

import dns.message
import logging
import sys

# remove current directory from path to load a module with the same name as us
oldpath, sys.path = sys.path, sys.path[1:]
import publicsuffix
sys.path = oldpath


"""
Module-level configuration
"""
TTL = 14400  # serve all records with this TTL
SERVE_TXT = True  # serve additional TXT records
LIST_FETCH = False  # download fresh copy of public suffix list
LIST_URL = "http://mxr.mozilla.org/mozilla-central/source/netwerk/dns/effective_tld_names.dat?raw=1"


log = logging.getLogger(__name__)
psl = publicsuffix.PublicSuffixList()


def configure_parser(parser):
    """
    Configure provided argparse subparser with module-level options.
    
    Use the set_defaults() construct as a callback for storing the parsed arguments.
    """

    def set_defaults(args):
        global TTL, SERVE_TXT, LIST_FETCH, LIST_URL

        TTL = args.publicsuffix_ttl
        SERVE_TXT = args.publicsuffix_txt

        if args.publicsuffix_fetch in (True, False):
            LIST_FETCH = args.publicsuffix_fetch
        else:
            LIST_FETCH = True
            LIST_URL = args.publicsuffix_fetch

        # download TLD list
        if LIST_FETCH:
            pass

    parser.set_defaults(func=set_defaults)
    parser.add_argument("--ttl", dest="publicsuffix_ttl", type=int,
                        default=TTL, metavar="TTL",
                        help="TTL to use for all records ")
    parser.add_argument("--fetch", dest="publicsuffix_fetch", nargs="?",
                        default=LIST_FETCH, const=True, metavar="URL",
                        help="fetch new list on start, from given URL if provided")
    parser.add_argument("--notxt", dest="publicsuffix_txt", action="store_false",
                        default=SERVE_TXT,
                        help="do not serve additional TXT records")

    return parser

def validate(msg):
    """
    Filter messages that are bad or we can't handle.
    
    Return a DNS rcode describing the problem.
    """
    opcode = msg.opcode()

    # we only support queries
    if opcode != dns.opcode.QUERY:
        return dns.rcode.NOTIMP

#     # we do not allow recursion
#     if msg.flags & dns.flags.RD:
#         return dns.rcode.REFUSED

    # only allow single question (qdcount=1)
    # @TODO: allow multiple questions?
    if len(msg.question) != 1:
        return dns.rcode.FORMERR

    return dns.rcode.NOERROR


def query(msg):
    """
    Return answer to provided DNS question.
     
    Create appropriate skeleton response message via dns.message.make_response(msg).
    """
    res = dns.message.make_response(msg)

    # validate query
    rcode = validate(msg)
    res.set_rcode(rcode)

    # stop here if didn't validate
    if rcode != dns.rcode.NOERROR:
        return res

    # this is just one query in reality, really, but let's not assume that
    for query in msg.question:

        name = query.name.to_unicode(omit_final_dot=True)

        # only deal with PTR queries
        if query.rdtype not in (dns.rdatatype.PTR, dns.rdatatype.ANY):
            res.set_rcode(dns.rcode.NXDOMAIN)
            log.info("Skipping query type %d", query.rdtype)
            continue

        try:
            suffix = psl.get_public_suffix(name)
        except:
            res.set_rcode(dns.rcode.SERVFAIL)
            log.exception("Oddness while looking up suffix")
            # don't process further questions since we've set rcode
            break

        if suffix:
            suffix += "."

            # answer section
            rdata = suffix
            # https://github.com/rthalley/dnspython/issues/44
            try:
                # dnspython3
                rrset = dns.rrset.from_text(query.name, TTL,
                        dns.rdataclass.IN, dns.rdatatype.PTR,
                        rdata)
            except AttributeError:
                # dnspython2
                rrset = dns.rrset.from_text(query.name, TTL,
                        dns.rdataclass.IN, dns.rdatatype.PTR,
                        rdata.encode("idna"))
            res.answer.append(rrset)

            if SERVE_TXT:
                # additional section
                tld = query.name.split(2)[-1].to_text(omit_final_dot=True)
                rdata = '"see: http://en.wikipedia.org/wiki/.{}"'.format(tld)
                # https://github.com/rthalley/dnspython/issues/44
                try:
                    # python3
                    rrset = dns.rrset.from_text(suffix, TTL,
                            dns.rdataclass.IN, dns.rdatatype.TXT,
                            rdata)
                except:
                    # python2
                    rrset = dns.rrset.from_text(suffix, TTL,
                            dns.rdataclass.IN, dns.rdatatype.TXT,
                            rdata.encode("latin1"))
                res.additional.append(rrset)

    return res
