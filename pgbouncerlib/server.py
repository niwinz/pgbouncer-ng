# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()

from collections import defaultdict
from gevent.server import StreamServer
from gevent.queue import Queue
from gevent.pool import Pool

import select
import socket
import struct
import logging as log
import os

from . import utils
from .settings import settings

def bind_unix_listener(path, reuse=False, backlog=100):
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) 
    
    if reuse:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect(path)

    else:
        utils.unlink(path)
        sock.bind(path)
        sock.listen(backlog) 

    return sock


class BouncerServer(StreamServer):
    queues = {}
    unix_socket_used = False

    def __init__(self):
        max_connections = settings.get_global_maxconns()
        local_connection_pool = Pool(max_connections)

        bind_host, bind_port = settings.get_local_host(), settings.get_local_port()
        if bind_host.startswith('unix'):
            sock = bind_unix_listener(bind_host[7:])
            log.info("Now listening on %s", bind_host)
            super(BouncerServer, self).__init__(sock)
            self.unix_socket_used = True
            return 
        
        log.info("Now listening on %s:%s", bind_host, bind_port)
        super(BouncerServer, self).__init__((bind_host, bind_port))


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
        bind_host, bind_port = settings.get_remote_host(), settings.get_remote_port()

        if bind_host.startswith('unix'):
            sock = bind_unix_listener(bind_host[7:], reuse=True)
        else:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            sock.connect((bind_host, bind_port))

        return False, sock


    def handle(self, source, address):
        log.debug("New remote client connected from %s", address)

        # ssl negotiation
        if not self.unix_socket_used:
            log.debug("SSL Negotiation. Temporary unsuported feature.")
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

                if _data == utils.make_terminate_bytes() or len(_data) == 0:
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
            utils.create_query_data("DISCARD ALL;"),
            utils.create_statement_description(),
            utils.create_flush_stetement(),
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
