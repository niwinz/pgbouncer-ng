SET(PGBOUNCER_SOURCES
    main.cpp
    server.cpp
    connection.cpp
)

SET(PGBOUNCER_HEADERS
    server.hpp
    connection.hpp
)

QT4_WRAP_CPP(PGBOUNCER_MOC ${PGBOUNCER_HEADERS})
ADD_EXECUTABLE(pgbouncer-cpp ${PGBOUNCER_SOURCES} ${PGBOUNCER_MOC})
TARGET_LINK_LIBRARIES(pgbouncer-cpp ${QT_LIBRARIES})
