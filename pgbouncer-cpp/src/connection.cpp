#include "connection.hpp"

Connection::Connection(int sock_descriptor, QObject *parent): QObject(parent) {
    this->sock_descriptor = sock_descriptor;
}

Connection::~Connection() {}

void Connection::accept() {
    this->socket.setSocketDescriptor(this->sock_descriptor);
    this->socket.waitForReadyRead(-1);

    QByteArray data = this->socket.readAll();
    this->socket.write("N\x00");

    this->socket.waitForReadyRead(-1);
    data = this->socket.readAll();
    qDebug() << data.toHex();

    QByteArray foo("\x00\x08\x00\x00\x00\x00S\x00\x00\x00\x1aapplication_name\x00psql\x00S\x00\x00\x00\x19client_encoding\x00UTF8\x00S\x00\x00\x00\x17DateStyle\x00ISO, MDY\x00S\x00\x00\x00\x19integer_datetimes\x00on\x00S\x00\x00\x00\x1bIntervalStyle\x00postgres\x00S\x00\x00\x00\x14is_superuser\x00on\x00S\x00\x00\x00\x19server_encoding\x00UTF8\x00S\x00\x00\x00\x19server_version\x009.1.3\x00S\x00\x00\x00!session_authorization\x00gemmed\x00S\x00\x00\x00#standard_conforming_strings\x00on\x00S\x00\x00\x00\x1bTimeZone\x00Europe/Madrid\x00K\x00\x00\x00\x0c\x00\x00+Y0\x87\x8e\xdcZ\x00\x00\x00\x05I\0");

    this->socket.write(foo);

    //this->connect(&this->socket, SIGNAL(readyRead()),
    //              this, SLOT(clientReadyRead()));
    //this->connect(&this->socket, SIGNAL(disconnected()),
    //              this, SLOT(deleteLater()));
}


void Connection::clientReadyRead() {
    QByteArray data = this->socket.readAll();
    qDebug() << "Received:" << data.toHex();
    qDebug() << (QByteArray::fromHex("0000000804d2162f") == data);
    socket.write("N\0");
}
