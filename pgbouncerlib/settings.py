# -*- coding: utf-8 -*-

from ConfigParser import ConfigParser, NoOptionError, NoSectionError
from os.path import expanduser, dirname, join, realpath

DEFAULT_CONFIG_FILES = [
    'pgbouncerng.ini', 
    expanduser('~/.config/pgbouncerng.ini'),
    '/usr/local/etc/pgbouncerng.ini',
    '/etc/pgbouncerng.ini'
]

DEFAULTS = {
    'local': {
        'host': 'unix:///tmp/.s.PGSQL.6666',
        'port': 6666,
        'ssl': False,
        'ssl_key': 'example_server.key',
        'ssl_crt': 'example_server.crt',
    },
    'remote': {
        'host': 'unix:///tmp/.s.PGSQL.5432',
        'port': 5432,
        'ssl': False,
    },
    'global': {
        'poolsize': 20,
        'maxconns': 200,
    }
}


class Settings(object):
    parser = ConfigParser()

    def __init__(self):
        self.parser.read(DEFAULT_CONFIG_FILES)

    def get_global_poolsize(self):
        try:
            poolsize = self.parser.get('global', 'poolsize')
        except ((NoOptionError, NoSectionError), NoSectionError):
            poolsize = DEFAULTS['global']['poolsize']
        return int(poolsize)

    def get_global_maxconns(self):
        try:
            maxconns = self.parser.get('global', 'maxconns')
        except (NoOptionError, NoSectionError):
            maxconns = DEFAULTS['global']['maxconns']
        return int(maxconns)

    def get_local_port(self):
        try:
            port = self.parser.get('local', 'port')
        except (NoOptionError, NoSectionError):
            port = DEFAULTS['local']['port']
        return port and int(port) or None

    def get_local_host(self):
        try:
            host = self.parser.get('local', 'host')
        except (NoOptionError, NoSectionError):
            host = DEFAULTS['local']['host']
        return host

    def get_local_ssl(self):
        try:
            sslopt = self.parser.getboolean('local', 'ssl')
        except (NoOptionError, NoSectionError):
            sslopt = DEFAULTS['local']['ssl']
        return sslopt

    def get_local_ssl_key(self):
        try:
            ssl_key = self.parser.get('local', 'ssl_key')
        except (NoOptionError, NoSectionError):
            ssl_key = DEFAULTS['local']['ssl_key']
        return ssl_key

    def get_local_ssl_crt(self):
        try:
            ssl_crt = self.parser.get('local', 'ssl_crt')
        except (NoOptionError, NoSectionError):
            ssl_crt = DEFAULTS['local']['ssl_crt']
        return ssl_crt

    def get_remote_port(self):
        try:
            port = self.parser.get('remote', 'port')
        except (NoOptionError, NoSectionError):
            port = DEFAULTS['remote']['port']
        return port and int(port) or None

    def get_remote_host(self):
        try:
            host = self.parser.get('remote', 'host')
        except (NoOptionError, NoSectionError):
            host = DEFAULTS['remote']['host']
        return host

    def get_remote_ssl(self):
        try:
            sslopt = self.parser.getboolean('remote', 'ssl')
        except (NoOptionError, NoSectionError):
            sslopt = DEFAULTS['remote']['ssl']
        return sslopt

    def remote_host_is_unix_socket(self):
        return self.get_remote_host().startswith('unix')

settings = Settings()
