#include <QtCore>
#include "server.hpp"

int main(int argc, char **argv) {
    QCoreApplication app(argc, argv);

    Server server;
    bool ok = server.listen(QHostAddress::Any, 6666);
    if (ok) {
        qDebug() << "Listening on 0.0.0.0:6666";
        return app.exec();
    }
    return -1;
}
