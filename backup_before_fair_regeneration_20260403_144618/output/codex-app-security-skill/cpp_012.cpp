static int createSocket(int family, int type, int protocol) {
#ifdef SOCK_CLOEXEC
        int fd = ::socket(family, type | SOCK_CLOEXEC, protocol);
        if (fd >= 0) {
            return fd;
        }
        if (errno != EINVAL) {
            throw std::system_error(errno, std::generic_category(), "socket creation failed");
        }
#endif
        int fd = ::socket(family, type, protocol);
        if (fd < 0) {
            throw std::system_error(errno, std::generic_category(), "socket creation failed");
        }