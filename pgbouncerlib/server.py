# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()

from collections import defaultdict
from gevent.server import StreamServer
from gevent.queue import Queue

import select
import socket
import struct
import logging as log


class BouncerServer(StreamServer):
    queues = {}

    def __init__(self):
        super(BouncerServer, self).__init__(('0.0.0.0', 6666))
    
    def make_ssl_request(self):
        """
        Temporal method.
        """
        return struct.pack("!ii", 8, 80877103)

    def make_terminate_bytes(self):
        """
        Returns terminate socket packet data.
        """

        return b'X\x00\x00\x00\x04'

    def create_dst_connection(self, client_data):
        """
        Creates dst connection. Id client_data key exists in queues pool, 
        return existing socket, otherwise create new socket.
        """
        log.debug("Creating socket for remote connection.")
        if client_data in self.queues and self.queues[client_data]['socket_queue'].qsize() > 0:
            log.debug("Remote connection found on pool, returning this.")
            return True, self.queues[client_data]['socket_queue'].get()
        
        log.debug("Connection not found on pool, creating new.")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect(('127.0.0.1', 5432))
        return False, sock

    def create_query_data(self, query):
        """
        Method for create binary representation of simple query.
        """

        buff = "\x00" + query + "\x00"
        buff = buff + struct.pack("!h", 0)
        buff = struct.pack("!i", len(buff) + 4) + buff
        return "P" + buff

    def create_statement_description(self):
        """
        Create statement binary representation.
        """

        buff = "S" + "\x00"
        buff = struct.pack("!i", len(buff) + 4) + buff
        return "D" + buff

    def create_flush_stetement(self):
        """
        Creates binary flush statement.
        """

        return 'H\x00\x00\x00\x04'

    def handle(self, source, address):
        log.debug("New remote client connected from %s", address)

        # ssl negotiation
        log.debug("SSL Negotiation. Temporary unsuported feature.")
        first_packet_data = source.recv(1024)
        source.send("N")
    
        # Receive client data (used for create peer key)
        log.debug("Waiting for client data...")
        client_data = source.recv(1024)

        # create or get from pool one socket
        from_pool, dst_sock = self.create_dst_connection(client_data)
        response = None

        if not from_pool:
            dst_sock.send(client_data)
            response = dst_sock.recv(1024)
            source.send(response)

        else:
            source.send(self.queues[client_data]['response'])

        error_generator, error = None, False
        
        log.debug("Entering on recv/send loop...")
        while not error:
            _r, _w, _e = select.select([source, dst_sock], [], [])

            for _in in _r:
                _data = _in.recv(1024)

                if _data == self.make_terminate_bytes() or len(_data) == 0:
                    error, error_generator = True, _in
                    break

                if _in == dst_sock:
                    source.send(_data)
                    continue

                dst_sock.send(_data)

        log.debug("Connection is closed in any socket.")
            
        # if error found on database, close all connections
        if error_generator != source:
            log.debug("Server connection is break. Closing all connections.")
            dst_sock.close()
            source.close()
            return

        log.debug("Client connection is break.")

        # send reset query
        send_data = [
            self.create_query_data("DISCARD ALL;"),
            self.create_statement_description(),
            self.create_flush_stetement(),
        ]
        dst_sock.send(b"".join(send_data))

        log.debug("Reset database connection state.")

        response_data = dst_sock.recv(1024)

        if client_data not in self.queues:
            self.queues[client_data] = {
                'socket_queue': Queue(),
                'response': response,
            }
        
        if self.queues[client_data]['socket_queue'].qsize() < 20:
            self.queues[client_data]['socket_queue'].put(dst_sock)

        log.debug("Returning connection to pool.")


    def parse_client_data(self, data):
        """
        Parse client_data. This method is not used.
        """

        first, last = data[:8], data[8:]
        length, protocol = struct.unpack("!ii", first)
        data_array = last.split("\x00")
        return length, protocol, data_array
