try {
            for (std::size_t i = 0; i < connectionCount; ++i) {
                int fd = ::socket(AF_INET, SOCK_STREAM, 0);
                if (fd == -1) {
                    int savedErrno = errno;
                    closeConnections(sockets);
                    throw std::runtime_error(
                        "failed to create socket " + std::to_string(i) + ": " +
                        std::strerror(savedErrno));
                }
                sockets.push_back(fd);
            }
        } catch (...) {
            closeConnections(sockets);
            throw;
        }