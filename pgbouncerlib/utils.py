# -*- coding: utf-8 -*-

import os
import struct

def unlink(path): 
    from errno import ENOENT 
    try: 
        os.unlink(path) 
    except OSError, ex: 
        if ex.errno != ENOENT: 
            raise 

def create_query_data(query):
    """
    Method for create binary representation of simple query.
    """

    buff = "\x00" + query + "\x00"
    buff = buff + struct.pack("!h", 0)
    buff = struct.pack("!i", len(buff) + 4) + buff
    return "P" + buff

def create_statement_description():
    """
    Create statement binary representation.
    """

    buff = "S" + "\x00"
    buff = struct.pack("!i", len(buff) + 4) + buff
    return "D" + buff


def create_flush_stetement():
    """
    Creates binary flush statement.
    """

    return 'H\x00\x00\x00\x04'


def parse_client_data(data):
    """
    Parse client_data. This method is not used.
    """

    first, last = data[:8], data[8:]
    length, protocol = struct.unpack("!ii", first)
    data_array = last.split("\x00")
    return length, protocol, data_array


def make_ssl_request():
    """
    Temporal method.
    """
    return struct.pack("!ii", 8, 80877103)


def make_terminate_bytes():
    """
    Returns terminate socket packet data.
    """

    return b'X\x00\x00\x00\x04'
