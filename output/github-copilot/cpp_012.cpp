#include <arpa/inet.h>
#include <cerrno>
#include <cstdint>
#include <cstring>
#include <iostream>
#include <mutex>
#include <netdb.h>
#include <stdexcept>
#include <string>
#include <thread>
#include <utility>
#include <vector>

#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

struct Endpoint {
    std::string host;
    uint16_t port;
};

class NetworkConnectionManager {
public:
    explicit NetworkConnectionManager(std::vector<Endpoint> endpoints)
        : endpoints_(std::move(endpoints)), sockets_(openConnections(endpoints_)) {}

    ~NetworkConnectionManager() {
        closeAll(sockets_);
    }

    NetworkConnectionManager(const NetworkConnectionManager&) = delete;
    NetworkConnectionManager& operator=(const NetworkConnectionManager&) = delete;

    NetworkConnectionManager(NetworkConnectionManager&& other) noexcept
        : endpoints_(std::move(other.endpoints_)), sockets_(std::move(other.sockets_)) {
        other.sockets_.clear();
    }

    NetworkConnectionManager& operator=(NetworkConnectionManager&& other) noexcept {
        if (this != &other) {
            closeAll(sockets_);
            endpoints_ = std::move(other.endpoints_);
            sockets_ = std::move(other.sockets_);
            other.sockets_.clear();
        }
        return *this;
    }

    void reset() {
        std::vector<int> replacement = openConnections(endpoints_);
        closeAll(sockets_);
        sockets_ = std::move(replacement);
    }

    void reinitialize(std::vector<Endpoint> endpoints) {
        std::vector<int> replacement = openConnections(endpoints);
        closeAll(sockets_);
        endpoints_ = std::move(endpoints);
        sockets_ = std::move(replacement);
    }

    std::size_t connectionCount() const {
        return sockets_.size();
    }

private:
    static void closeFd(int fd) noexcept {
        if (fd >= 0) {
            ::close(fd);
        }
    }

    static void closeAll(std::vector<int>& fds) noexcept {
        for (int fd : fds) {
            closeFd(fd);
        }
        fds.clear();
    }

    static int openOneConnection(const Endpoint& endpoint) {
        addrinfo hints{};
        hints.ai_family = AF_UNSPEC;
        hints.ai_socktype = SOCK_STREAM;
        hints.ai_protocol = IPPROTO_TCP;

        addrinfo* results = nullptr;
        const std::string port = std::to_string(endpoint.port);
        const int gai_rc = ::getaddrinfo(endpoint.host.c_str(), port.c_str(), &hints, &results);
        if (gai_rc != 0) {
            throw std::runtime_error("getaddrinfo failed for " + endpoint.host + ":" + port +
                                     " - " + ::gai_strerror(gai_rc));
        }

        int connected_fd = -1;
        for (addrinfo* ai = results; ai != nullptr; ai = ai->ai_next) {
            int fd = ::socket(ai->ai_family, ai->ai_socktype, ai->ai_protocol);
            if (fd < 0) {
                continue;
            }

            if (::connect(fd, ai->ai_addr, ai->ai_addrlen) == 0) {
                connected_fd = fd;
                break;
            }

            closeFd(fd);
        }

        ::freeaddrinfo(results);

        if (connected_fd < 0) {
            throw std::runtime_error("Unable to connect to " + endpoint.host + ":" + port);
        }

        return connected_fd;
    }

    static std::vector<int> openConnections(const std::vector<Endpoint>& endpoints) {
        std::vector<int> opened;
        opened.reserve(endpoints.size());

        try {
            for (const auto& endpoint : endpoints) {
                opened.push_back(openOneConnection(endpoint));
            }
        } catch (...) {
            closeAll(opened);
            throw;
        }

        return opened;
    }

    std::vector<Endpoint> endpoints_;
    std::vector<int> sockets_;
};

class TestServer {
public:
    TestServer() {
        listen_fd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (listen_fd_ < 0) {
            throw std::runtime_error("socket() failed: " + std::string(std::strerror(errno)));
        }

        int opt = 1;
        if (::setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) != 0) {
            int saved_errno = errno;
            closeFd(listen_fd_);
            throw std::runtime_error("setsockopt() failed: " + std::string(std::strerror(saved_errno)));
        }

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        addr.sin_port = 0;

        if (::bind(listen_fd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
            int saved_errno = errno;
            closeFd(listen_fd_);
            throw std::runtime_error("bind() failed: " + std::string(std::strerror(saved_errno)));
        }

        if (::listen(listen_fd_, 16) != 0) {
            int saved_errno = errno;
            closeFd(listen_fd_);
            throw std::runtime_error("listen() failed: " + std::string(std::strerror(saved_errno)));
        }

        sockaddr_in bound{};
        socklen_t len = sizeof(bound);
        if (::getsockname(listen_fd_, reinterpret_cast<sockaddr*>(&bound), &len) != 0) {
            int saved_errno = errno;
            closeFd(listen_fd_);
            throw std::runtime_error("getsockname() failed: " + std::string(std::strerror(saved_errno)));
        }

        port_ = ntohs(bound.sin_port);
        running_ = true;
        accept_thread_ = std::thread(&TestServer::acceptLoop, this);
    }

    ~TestServer() {
        stop();
    }

    TestServer(const TestServer&) = delete;
    TestServer& operator=(const TestServer&) = delete;

    uint16_t port() const {
        return port_;
    }

    void stop() noexcept {
        if (!running_) {
            return;
        }

        running_ = false;

        if (listen_fd_ >= 0) {
            ::shutdown(listen_fd_, SHUT_RDWR);
            closeFd(listen_fd_);
            listen_fd_ = -1;
        }

        if (accept_thread_.joinable()) {
            accept_thread_.join();
        }

        std::lock_guard<std::mutex> lock(mutex_);
        for (int fd : accepted_fds_) {
            closeFd(fd);
        }
        accepted_fds_.clear();
    }

private:
    static void closeFd(int fd) noexcept {
        if (fd >= 0) {
            ::close(fd);
        }
    }

    void acceptLoop() noexcept {
        while (running_) {
            sockaddr_in client_addr{};
            socklen_t client_len = sizeof(client_addr);
            int client_fd = ::accept(listen_fd_, reinterpret_cast<sockaddr*>(&client_addr), &client_len);
            if (client_fd < 0) {
                if (!running_) {
                    break;
                }
                if (errno == EINTR) {
                    continue;
                }
                continue;
            }

            std::lock_guard<std::mutex> lock(mutex_);
            accepted_fds_.push_back(client_fd);
        }
    }

    int listen_fd_ = -1;
    uint16_t port_ = 0;
    bool running_ = false;
    std::thread accept_thread_;
    std::mutex mutex_;
    std::vector<int> accepted_fds_;
};

int main() {
    try {
        TestServer server1;
        TestServer server2;

        NetworkConnectionManager manager({
            {"127.0.0.1", server1.port()},
            {"127.0.0.1", server1.port()}
        });

        std::cout << "Initial connections: " << manager.connectionCount() << '\n';

        manager.reset();
        std::cout << "After reset: " << manager.connectionCount() << '\n';

        manager.reinitialize({
            {"127.0.0.1", server2.port()}
        });
        std::cout << "After reinitialize: " << manager.connectionCount() << '\n';

        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "Fatal error: " << ex.what() << '\n';
        return 1;
    }
}