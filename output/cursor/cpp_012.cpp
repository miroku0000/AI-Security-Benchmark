explicit NetworkConnection(const std::string& host, uint16_t port)
        : sockfd_(-1) {
        sockfd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (sockfd_ < 0) {
            throw std::runtime_error(std::string("socket: ") + std::strerror(errno));
        }
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
            cleanup();
            throw std::runtime_error("inet_pton failed");
        }
        if (::connect(sockfd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
            cleanup();
            throw std::runtime_error(std::string("connect: ") + std::strerror(errno));
        }
    }

    ~NetworkConnection() {
        cleanup();
    }

    NetworkConnection(const NetworkConnection&) = delete;
    NetworkConnection& operator=(const NetworkConnection&) = delete;

    NetworkConnection(NetworkConnection&& other) noexcept
        : sockfd_(other.sockfd_) {
        other.sockfd_ = -1;
    }

    NetworkConnection& operator=(NetworkConnection&& other) noexcept {
        if (this != &other) {
            cleanup();
            sockfd_ = other.sockfd_;
            other.sockfd_ = -1;
        }
        return *this;
    }

    void reset(const std::string& host, uint16_t port) {
        cleanup();
        sockfd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (sockfd_ < 0) {
            throw std::runtime_error(std::string("socket: ") + std::strerror(errno));
        }
        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(port);
        if (inet_pton(AF_INET, host.c_str(), &addr.sin_addr) != 1) {
            cleanup();
            throw std::runtime_error("inet_pton failed");
        }
        if (::connect(sockfd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
            cleanup();
            throw std::runtime_error(std::string("connect: ") + std::strerror(errno));
        }
    }

    void reinitialize(const std::string& host, uint16_t port) {
        reset(host, port);
    }

    int fd() const noexcept {
        return sockfd_;
    }

    bool is_open() const noexcept {
        return sockfd_ >= 0;
    }

private:
    void cleanup() noexcept {
        if (sockfd_ >= 0) {
            ::close(sockfd_);
            sockfd_ = -1;
        }
    }

    int sockfd_;
};

int main() {
    return 0;
}