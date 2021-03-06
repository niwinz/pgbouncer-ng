# -*- coding: utf-8 -*-

from gevent import monkey
monkey.patch_all()

from collections import defaultdict
from gevent.server import StreamServer
from gevent.queue import Queue
from gevent.pool import Pool
from gevent.ssl import wrap_socket
from gevent.queue import Empty

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
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    if reuse:
        sock.connect((bind_host, bind_port))
    else:        
        sock.bind((bind_host, bind_port))
        sock.listen(backlog) 
    
    return sock


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


def blocking_read_until_nodata(sock):
    retval = []
    while True:
        data = sock.recv(1024)
        if not data:
            break

        retval.append(data)
    return "".join(retval)
        

class BouncerServer(StreamServer):
    queues = {}
    unix_socket_used = False
    remote_unix_socket_used = False

    def __del__(self):
        for name, queue in self.queues.iteritems():
            try:
                sock, _, _, _ = queue.get(False)
                sock.close()
            except Empty:
                pass
        self.close()

    def __init__(self):
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
        super(BouncerServer, self).__init__(sock)

    def create_dst_connection(self, client_data):
        """
        Creates dst connection. Id client_data key exists in queues pool, 
        return existing socket, otherwise create new socket.
        """
        
        log.debug("Creating socket for remote connection.")
        if client_data in self.queues and self.queues[client_data].qsize() > 0:
            log.debug("Remote connection found on pool, returning this.")
            socket, response, auth_response = self.queues[client_data].get()
            return True, socket, response, auth_response
        
        log.debug("Connection not found on pool, creating new.")
        bind_host, bind_port = settings.get_remote_host(), settings.get_remote_port()

        if bind_host.startswith('unix'):
            sock = bind_unix_listener(bind_host[7:], reuse=True)
        else:
            sock = bind_tcp_listener(bind_host, bind_port, reuse=True)

        return False, sock, None, None

    def check_auth_error(self, response):
        if response and response[0] != 'E':
            return False
        return True

    def handle_authentication(self, source, dst_sock):
        """
        Method for correct handle authentications for new conenctions.
        """

        response = dst_sock.recv(1024)
        source.send(response)

        auth_error, auth_response = False, False

        auth_code = struct.unpack("!i", response[5:][:4])[0]
        if auth_code == 5:
            log.debug("Authenticating client...")
            user_pass = source.recv(1024)
            dst_sock.send(user_pass)
            auth_response = dst_sock.recv(1024)
            
            auth_error = self.check_auth_error(auth_response)
            self.send(source, auth_response)
        return auth_error, response, auth_response

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

        response, auth_response = None, None
    
        # Receive client data (used for create peer key)
        log.debug("Waiting for client data...")
        client_data = source.recv(2024)
        
        # create or get from pool one socket
        from_pool, dst_sock, response, auth_response = self.create_dst_connection(client_data)
        remote_ssl_opt = settings.get_remote_ssl()

        if not from_pool:
            # send ssl negotiation with remote server
            if remote_ssl_opt and not self.remote_unix_socket_used:
                dst_sock.send(utils.make_ssl_request())
                rsp = dst_sock.recv(1024)
                if rsp[0] == "S":
                    dst_sock = wrap_socket(dst_sock)
                else:
                    raise Exception("Server does not support ssl connections")

            dst_sock.send(client_data)
            auth_error, response, auth_response = self.handle_authentication(source, dst_sock)
        
        else:
            auth_code = struct.unpack("!i", response[5:][:4])[0]
            if auth_code == 5:
                log.debug("Authenticating client...")
                source.send(auth_response)
            else:
                source.send(response)

        error_generator, auth_error, error = None, False, False
        
        source.setblocking(0)
        dst_sock.setblocking(0)
        
        log.debug("Entering on recv/send loop...")
        
        while not error:
            _r, _w, _e = select.select([source, dst_sock], [], [])

            for _in in _r:
                _data = read_until_fail(_in)

                if not _data or _data[0] == b'X':
                    error, error_generator = True, _in
                    break

                if _data[0] == 'E':
                    self.send(source, _data)
                    error, auth_error = True, True

                if _in == dst_sock:
                    ok = self.send(source, _data)
                    if not ok:
                        error, error_generator = True, _in
                        break
                else:
                    self.send(dst_sock, _data)

        log.debug("Connection is closed in any socket.")
            
        # if error found on database or authentication error, close all connections
        if error_generator != source or auth_error:
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
        
        ok = False
        if _data:
            ok = self.send(dst_sock, b"".join(send_data))
            
        if ok:
            log.debug("Reset database connection state.")
            response_data = read_until_fail(dst_sock)
            
            if client_data not in self.queues:
                self.queues[client_data] = Queue()
            
            if self.queues[client_data].qsize() < 30:
                self.queues[client_data].put((dst_sock, response, auth_response))

            log.debug("Returning connection to pool.")
            log.debug("Current pool size: %s", self.queues[client_data].qsize())
        else:
            dst_sock.close()

    def send(self, sock, data):
        try:
            sock.send(data)
            return True
        except socket.error as e:
            print "Socket.Error", str(e)
            return False

        except IOError as e:
            print "IOError:", e.errno
            return False
