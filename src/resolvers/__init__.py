# -:- coding: utf-8 -:-
#
# Back-end resolver modules.
#
# Each module should expose the following module level constants:
#
#     NAME
#     HELP
#     DESC
#
# and methods:
#
#     def configure_parser(parser):
#         """
#         Configure provided argparse subparser with module-level options.
#         
#         Use the set_defaults() construct as a callback for storing the parsed arguments.
#         """
#         pass
#     
#     def query(msg):
#         """
#         Return answer to provided DNS question.
#         
#         Create appropriate skeleton response message via dns.message.make_response(msg).
#         """
#         pass
#