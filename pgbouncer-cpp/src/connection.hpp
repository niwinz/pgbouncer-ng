#ifndef PGBOUNCER_CONNECTION_HPP
#define PGBOUNCER_CONNECTION_HPP

#include <QtCore>
#include <QtNetwork>

class Connection: public QObject {
    Q_OBJECT
public:
    Connection(int sock_descriptor, QObject *parent = 0);
    ~Connection();

    void accept();

private:
    int sock_descriptor;
    QTcpSocket socket;

private slots:
    void clientReadyRead();
};

#endif
