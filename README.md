# pgbouncer-ng #

Ligthweight connection pooler for PostgreSQL (completely written in python).

## Features: ##

* Without authentication, everything is delegated to postgresql.
* Ssl support, both at the pool, and in connection to postgresql.

## How to install? ##

Fetch latest development branch from github and install this:
    
    git clone git://github.com/niwibe/pgbouncer-ng.git
    cd pgbouncer-ng
    sudo python setup.py install

*NOTE:* gevent-1.0b1+ is required dependence.

## How to configure: ##

The configuration is divided into 3 groups: global, local, remote. In global scope you
can define limits for pooler. In local scope you can define settings for local pool:
bind address or/and port, ssl certificate and ssl private key. And remote scope, you can 
define settings for remote postgresql connection.

In pgbouncerng.ini has sample/default configuration.

The order of search configuration file is:

- ``./pgbouncerng.ini``
- ``~/.config/pgbouncerng.ini``
- ``/usr/local/etc/pgbouncerng.ini``
- ``/etc/pgbouncerng.ini``
