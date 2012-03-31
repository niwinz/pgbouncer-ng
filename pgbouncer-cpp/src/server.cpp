#include "server.hpp"
#include "connection.hpp"

Server::Server(QObject *parent): QTcpServer(parent) {}
Server::~Server() {};

void Server::incomingConnection(int sock_descriptor) {
    Connection *connection = new Connection(sock_descriptor, this);
    connection->accept();
};
