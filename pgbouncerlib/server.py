# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()

from collections import defaultdict
from gevent.server import StreamServer
from gevent.queue import Queue
from gevent.pool import Pool
from gevent.ssl import wrap_socket

import select
import socket
import struct
import logging as log
import os
import stat
import sys
import ssl

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
    
    
def bind_tcp_listener(bind_host, bind_port, reuse=False, backlog=100):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    if reuse:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect((bind_host, bind_port))
    else:        
        sock.bind((bind_host, bind_port))
        sock.listen(backlog) 
    
    return sock

def read_bytes(sock, byte_count):
    retval = []
    bytes_read = 0
    while bytes_read < byte_count:
        addt_data = sock.recv(1024)
        bytes_read += len(addt_data)
        
        print bytes_read, byte_count
        
        #~ assert bytes_read <= byte_count
        retval.append(addt_data)
    return "".join(retval)

def read_message(sock):
    bytes = read_bytes(sock, 5)   
    message_code = bytes[0]   
    data_len = struct.unpack("!i", bytes[1:])[0] - 4
    bytes = read_bytes(sock, data_len)
    assert len(bytes) == data_len
    return bytes

def read_until_fail(sock):
    retval = []
    more_data=True
    while more_data:
        try:
            read_data = sock.recv(1024)
            retval.append(read_data)
            more_data = len(read_data)>0
        except:
            more_data=False    
    return "".join(retval)

class BouncerServer(StreamServer):
    queues = {}
    unix_socket_used = False
    remote_unix_socket_used = False

    def __init__(self):
        max_connections = settings.get_global_maxconns()
        local_connection_pool = Pool(max_connections)

        bind_host, bind_port = settings.get_local_host(), settings.get_local_port()
        if bind_host.startswith('unix'):
            sock = bind_unix_listener(bind_host[7:])
            log.info("Now listening on %s", bind_host)
            self.unix_socket_used = True
        else:
            sock = bind_tcp_listener(bind_host, bind_port)
            log.info("Now listening on %s:%s", bind_host, bind_port)

        current_path = os.path.abspath(".")
        self.local_ssl_opt, self.local_ssl_key, self.local_ssl_cert = (
            settings.get_local_ssl(),
            os.path.join(current_path, settings.get_local_ssl_key()),
            os.path.join(current_path, settings.get_local_ssl_crt())
        )

        # check ssl files permissions
        if self.local_ssl_opt:
            key_file_uid = os.stat(self.local_ssl_key).st_uid
            crt_file_uid = os.stat(self.local_ssl_cert).st_uid

            try:
                assert key_file_uid == os.getuid()
                assert crt_file_uid == os.getuid()
            except AssertionError:
                log.error("Incorrect permissions on key and cert file.")
                sys.exit(-1)

            mode = stat.S_IMODE(os.stat(self.local_ssl_key).st_mode)
            if mode & stat.S_IWUSR == 0 or mode & stat.S_IRUSR == 0 \
                    or mode & stat.S_IRGRP != 0 \
                    or mode & stat.S_IWGRP != 0 \
                    or mode & stat.S_IROTH != 0 \
                    or mode & stat.S_IWOTH != 0:
                log.error("Incorrect permissions on key file")
                sys.exit(-1)

        self.remote_unix_socket_used = settings.remote_host_is_unix_socket()
        super(BouncerServer, self).__init__(sock, spawn=local_connection_pool)

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
            sock = bind_tcp_listener(bind_host, bind_port, reuse=True)

        return False, sock

    def handle(self, source, address):
        log.debug("New remote client connected from %s", address)

        # ssl negotiation
        if not self.unix_socket_used:
            ssl_req_data = source.recv(1024)
            if self.local_ssl_opt:
                log.debug("SSL Negotiation.")
                source.send("S")
                source = wrap_socket(source, keyfile=self.local_ssl_key, 
                    certfile=self.local_ssl_cert, server_side=True)
                source.settimeout(60)
            else:
                source.send("N")

        response = None
    
        # Receive client data (used for create peer key)
        log.debug("Waiting for client data...")
        client_data = source.recv(1024)

        # create or get from pool one socket
        from_pool, dst_sock = self.create_dst_connection(client_data)
        remote_ssl_opt = settings.get_remote_ssl()

        if not from_pool:
            # send ssl negotiation
            if remote_ssl_opt and not self.remote_unix_socket_used :
                dst_sock.send(utils.make_ssl_request())
                rsp = dst_sock.recv(1024)
                if rsp[0] == "S":
                    dst_sock = wrap_socket(dst_sock)
                else:
                    raise Exception("Server does not support ssl connections")

            dst_sock.send(client_data)
            response = dst_sock.recv(1024)
            source.send(response)

        else:
            source.send(self.queues[client_data]['response'])

        error_generator, error = None, False
        
        source.setblocking(0)
        dst_sock.setblocking(0)
        
        log.debug("Entering on recv/send loop...")
        while not error:
            _r, _w, _e = select.select([source, dst_sock], [], [])

            for _in in _r:
                _data = read_until_fail(_in)
                
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

        response_data = read_until_fail(dst_sock)
        
        if client_data not in self.queues:
            self.queues[client_data] = {
                'socket_queue': Queue(),
                'response': response,
            }
        
        if self.queues[client_data]['socket_queue'].qsize() < 20:
            self.queues[client_data]['socket_queue'].put(dst_sock)

        log.debug("Returning connection to pool.")
        log.debug("Current pool size: %s", self.queues[client_data]['socket_queue'].qsize())
