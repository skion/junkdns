#!/usr/bin/env python
# -:- coding: utf-8 -:-

"""
JunkDNS - An experimental DNS resolver to query data sets via DNS.
"""

#
# TODO:
# - Deduplicate UDP vs TCP code
# - Unicode support
# - Proper logging
# - Proper daemonize
#

from __future__ import absolute_import

import argparse
import logging
import pkgutil
import struct
import threading

import dns.message

try:
    # python 3
    import socketserver
except ImportError:
    # python 2
    import SocketServer as socketserver


log = logging.getLogger(__name__)

# look for resolver modules here
RESOLVERS_PATH = "resolvers"


def from_wire(data, origin=None):
    return dns.message.from_wire(data, origin=origin)


def to_wire(msg, origin):
    if msg:
        return msg.to_wire(origin=origin)
    else:
        return None


class DnsRequestHandler(socketserver.BaseRequestHandler):

    resolver = None  # DNS resolver module to query
    origin = None  # DNS origin to serve from; None means root


class DnsUdpRequestHandler(DnsRequestHandler):
    """
    Single-threaded UDP request handler
    """

    def handle(self):
        data, socket = self.request

        # TODO this could go in class init for speed
        if self.origin:
            origin = dns.name.from_text(self.origin)
        else:
            origin = None

        # TODO if fails, return SRVFAIL
        msg = from_wire(data, origin)

        log.info("Handling query for: %s", msg.question)
        log.debug("Message is: %s", msg)

        try:
            res = self.resolver.query(msg)
            log.debug("Response is: %s", res)
        except:
            log.exception("Oddness while processing query")
            raise
            # @TODO should give a SERVFAIL here instead of nothing
        else:
            if res:
                data = to_wire(res, origin)
                socket.sendto(data, self.client_address)
            else:
                log.warning("No result from query")


class DnsTcpRequestHandler(DnsRequestHandler):
    """
    Threaded TCP request handler
    """

    def handle(self):

        data = self.request.recv(2)
        length = struct.unpack("!H", data)[0]
        data = self.request.recv(length)

        # TODO this could go in class init for speed
        if self.origin:
            origin = dns.name.from_text(self.origin)
        else:
            origin = None

        msg = from_wire(data, origin)

        try:
            res = self.resolver.query(msg)
        except:
            log.exception("Oddness while processing query")
            # @TODO should give a SERVFAIL here instead of nothing
        else:
            if res:
                cur_thread = threading.current_thread()
                log.debug("Reply from thread %s: %s", cur_thread, res)

                data = to_wire(res, origin)
                wire = struct.pack("!H", len(data)) + data
                self.request.sendall(wire)
            else:
                log.warning("No result from query")


def load_modules(path):
    """
    Load modules in directory pointed to by path dynamically.

    From http://stackoverflow.com/a/8556471/543431
    """
    modules = dict()
    for importer, name, _ in pkgutil.iter_modules([path]):
        pkgname = path + "." + name
        module = importer.find_module(name).load_module(pkgname)
        modules[name] = module
    return modules


if __name__ == "__main__":

    parser = argparse.ArgumentParser(prog="junkdns",
                                     description="An experimental DNS resolver to query data sets via DNS.")

    parser.add_argument("--host", "-H", dest="host", default="localhost",
                       help="host or IP address to bind to (default: %(default)s)")
    parser.add_argument("--port", "-P", dest="port", type=int, default=5053,
                       help="port number to bind to (default: %(default)d)")
    parser.add_argument("--origin", "-O", dest="origin", default=".",
                       help="DNS origin to use, e.g. _tldns.mydomain.com. (default: %(default)s)")
    parser.add_argument("--tcp", "-t", dest="tcp", action="store_true",
                       help="start a TCP listener on the same port")
#     parser.add_argument("--pool", "-p", dest="pool", type=int, default=10,
#                        help="thread pool size of TCP listener (default: %(default)d)")
    parser.add_argument("--debug", "-D", dest="debug", default="warn",
                        choices=["debug", "info", "warn", "error"],
                        help="debugging level")

    # add resolver-specific section
    subparsers = parser.add_subparsers(dest="resolver",  # used to find the selected resolver
                                        title="resolver modules",
                                        description="%(prog)s supports multiple resolvers, but only one at a time. "
                                                    "Run multiple resolvers as separate daemons.",
                                        help="available resolvers")

    # load resolver modules
    resolvers = load_modules(RESOLVERS_PATH)
    for name, module in resolvers.iteritems():
        try:
            subparser = subparsers.add_parser(name=module.NAME,
                                              help=module.HELP,
                                              description=module.DESC)
        except AttributeError:
            # logging is not initialised here yet
            raise RuntimeError("Resolver module {} should sport NAME, HELP and DESC.".format(name))
        else:
            module.configure_parser(subparser)

    args = parser.parse_args()

    # configure log level
    loglevel = eval("logging.{}".format(args.debug.upper()))
    logging.basicConfig(level=loglevel)

    # find chosen resolver
    resolver = resolvers[args.resolver]

    # set module-specific arguments via the set_defaults() function provided by module
    try:
        args.func(args)
    except AttributeError:
        pass

    # set request handler defaults (both UDP and TCP)
    DnsRequestHandler.resolver = resolver
    DnsRequestHandler.origin = args.origin

    tcpserver = tcpthread = None
    
    # tread out threaded tcp server
    if args.tcp:
        socketserver.ThreadingTCPServer.allow_reuse_address = True
        tcpserver = socketserver.ThreadingTCPServer((args.host, args.port),
                                                    DnsTcpRequestHandler)
        tcpthread = threading.Thread(name="tcp", target=tcpserver.serve_forever)
        tcpthread.start()

    # run single-threaded udp server in main thread
    socketserver.UDPServer.allow_reuse_address = True
    udpserver = socketserver.UDPServer((args.host, args.port),
                                       DnsUdpRequestHandler)
    try:
        udpserver.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        udpserver.server_close()
        if tcpserver:
            tcpserver.shutdown()
            tcpserver.server_close()
        if tcpthread:
            tcpthread.join()
