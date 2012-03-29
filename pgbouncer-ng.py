# -*- coding: utf-8 -*-

from pgbouncerlib.server import BouncerServer
import logging

if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s: %(message)s', level=logging.DEBUG)
    # uncomment this for disable logging
    # TODO: implement good argument parsing with http://docs.python.org/library/argparse.html
    #logging.disable(logging.DEBUG)

    server = BouncerServer()
    server.serve_forever()
