#ifndef PGBOUNCER_SERVER_HPP
#define PGBOUNCER_SERVER_HPP

#include <QtCore>
#include <QtNetwork>

class Server: public QTcpServer {
    Q_OBJECT
public:
    Server(QObject *parent = 0);
    ~Server();

protected:
    virtual void incomingConnection(int);
};

#endif
