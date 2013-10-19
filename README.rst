--------------
JunkDNS README
--------------
*An experimental DNS resolver to query data sets via DNS.*


Introduction
------------
`JunkDNS`, analogue to junk DNA, is a simple DNS server that serves information 
normally not coded in DNS.

Its intended use is to run behind a local caching DNS resolver, and thus allow
local clients to perform queries without any configuration or reliance on 
bindings for some other key-value store.

Included is a resolver for PublicSuffix_ extensions, and one for LOCODE_ 
location identifiers is planned.

.. _PublicSuffix: http://publicsuffix.org/
.. _LOCODE: http://www.unece.org/cefact/locode/welcome.html


Usage
-----
`JunkDNS` is started by selecting one of the available resolver modules as an
argument. Check the command line help for available options::

   $ python junkdns.py --help
   usage: junkdns [-h] [--host HOST] [--port PORT] [--origin ORIGIN] [--tcp]
               [--debug {debug,info,warn,error}]
               {publicsuffix} ...

   An experimental DNS resolver to query data sets via DNS.
   
   optional arguments:
     -h, --help            show this help message and exit
     --host HOST, -H HOST  host or IP address to bind to (default: localhost)
     --port PORT, -P PORT  port number to bind to (default: 5053)
     --origin ORIGIN, -O ORIGIN
                           DNS origin to use, e.g. _tldns.mydomain.com. (default:
                           .)
     --tcp, -t             start a TCP listener on the same port
     --debug {debug,info,warn,error}, -D {debug,info,warn,error}
                           debugging level
   
   resolver modules:
     junkdns supports multiple resolvers, but only one at a time. Run multiple
     resolvers as separate daemons.
   
     {publicsuffix}        available resolvers
       publicsuffix        a resolver to query top-level domains via
                           publicsuffix.org

Resolver-specific details and command line options can be queried by placing
the `--help` option *after* the resolver name::

   $ python junkdns.py publicsuffix --help
   usage: junkdns publicsuffix [-h] [--ttl TTL] [--fetch [URL]] [--notxt]
   
   This resolver returns a PTR record pointing to the top-level domain of the
   hostname in question. When the --txt option is given, it will also return
   additional informational TXT records. The list of current top-level domains
   can be explicitly downloaded upon startup via the --fetch argument.
   
   optional arguments:
     -h, --help     show this help message and exit
     --ttl TTL      TTL to use for all records
     --fetch [URL]  fetch new list on start, from given URL if provided
     --notxt        do not serve additional TXT records

To start the server as a local service, try this::

   $ python junkdns.py -D info publicsuffix

After that, a DNS query for the public suffix of host name `www.test.co.uk`::

   $ dig @localhost -p 5053 +nocmd www.test.co.uk PTR

will answer with a pointer to the domain part of the host::

   ;; Got answer:
   ;; ->>HEADER<<- opcode: QUERY, status: NOERROR, id: 53179
   ;; flags: qr rd; QUERY: 1, ANSWER: 1, AUTHORITY: 0, ADDITIONAL: 2
   ;; WARNING: recursion requested but not available
   
   ;; OPT PSEUDOSECTION:
   ; EDNS: version: 0, flags:; udp: 8192
   ;; QUESTION SECTION:
   ;www.test.co.uk.        IN PTR
   
   ;; ANSWER SECTION:
   www.test.co.uk.      14400 IN PTR   test.co.uk.
   
   ;; ADDITIONAL SECTION:
   test.co.uk.    14400 IN TXT   "see: http://en.wikipedia.org/wiki/.co.uk"
   
   ;; Query time: 2 msec
   ;; SERVER: 127.0.0.1#5053(127.0.0.1)
   ;; WHEN: Sat Oct 12 21:48:33 2013
   ;; MSG SIZE  rcvd: 110


Gateway configuration
---------------------
In the above setup, the client (`dig` in this case) needs to be configured to
connect to the special DNS server, which in many cases is cumbersome. If you
want to avoid this, configure a gateway DNS server or recursor to delegate 
part of the DNS namespace to `JunkDNS` instead.

- Choose a domain to delegate, e.g. `_tldns.mydomain.invalid`
- Configure your DNS recursor to forward any queries for the above domain to
  `JunkDNS`
- Configure `JunkDNS` with the `--origin` option to run on the delegated domain::

    $ python junkdns.py -D info -O _tldns.mydomain.invalid publicsuffix

After that, and assuming the gateway is configured as the system DNS resolver, 
just query::

   $ dig +short www.test.co.uk._tldns.mydomain.invalid
   test.co.uk

`Unbound`_ is capable of this by means of a `stub-zone`::

   server:
      # we do query the stub zone on localhost
      do-not-query-localhost: no
      
      # ignore chain of trust
      domain-insecure: "_tldns.mydomain.invalid"
      
   # junkdns server running here with option:
   # --origin _tldns.mydomain.invalid
   stub-zone:
      name: "_tldns.mydomain.invalid"
      stub-addr: 127.0.0.1@5053
      stub-prime: no
      stub-first: no

There seems to be a bug_ in `Unbound` version 1.4.17, which can be worked around by replacing the `stub-zone` with a `forward-zone`.

.. _Unbound: http://unbound.net/
.. _bug: https://www.nlnetlabs.nl/bugs-script/show_bug.cgi?id=528


Public delegation
-----------------
I would not immediately recommend doing this, but if the DNS cache in the above 
example is publicly accessible, then it is possible to delegate a domain to `JunkDNS` publicly as well.
Do this by adding an NS record for the domain to the parent zone file, pointing to the public IP of the server,
and adding the following configuration options to Unbound::

   server:
      # allow non-recursive (snoop) queries to world
      # (otherwise queries through your ISP's recursor will fail)
      access-control: 0.0.0.0/0 allow_snoop
      access-control: 127.0.0.0/8 allow_snoop
      access-control: ::0/0 allow_snoop
      access-control: ::1 allow_snoop
      access-control: ::ffff:127.0.0.1 allow_snoop

      # refuse all queries except our zone
      local-zone: "." deny
      local-zone: "_tldns.mydomain.invalid" transparent

There's a demo service running with this configuration on::

   $ dig +short www.test.co.uk._tldns.dnsben.ch PTR
   test.co.uk

Try it out!


Hacking
-------
`JunkDNS` uses the excellent DNSPython_ library for all DNS magic and wire 
conversions.

Although the resolver module API should not be considered stable at all, adding 
a new resolver only requires two functions and their implementation should be
straightforward. The `resolvers/publicsuffix.py` module can be used as an example
for now.  

.. image:: https://api.travis-ci.org/skion/junkdns.png
   :alt: Travis build status
   :target: https://travis-ci.org/skion/junkdns/

.. _DNSPython: http://www.dnspython.org/


To do
-----

- Python 3 support
- Make UDP server threaded too
- Make servers use a thread pool
- Add non-blocking gevent server option
- Listen on Unix domain sockets
- Add DNS ID check
- Properly daemonise
- Add Debian packaging
- Add LOCODE resolver
- Resolver agnostic tests
- Concurrency tests
