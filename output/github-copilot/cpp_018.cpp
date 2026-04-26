#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <condition_variable>
#include <cstring>
#include <exception>
#include <functional>
#include <iostream>
#include <memory>
#include <mutex>
#include <queue>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>

class SocketError : public std::runtime_error {
public:
    explicit SocketError(const std::string& message) : std::runtime_error(message) {}
};

static void throwSystemError(const std::string& prefix) {
    throw SocketError(prefix + ": " + std::strerror(errno));
}

struct Endpoint {
    std::string host;
    uint16_t port;
};

class Connection {
public:
    Connection(std::size_t id, Endpoint endpoint)
        : id_(id), endpoint_(std::move(endpoint)), sockfd_(-1) {}

    ~Connection() {
        closeSocket();
    }

    Connection(const Connection&) = delete;
    Connection& operator=(const Connection&) = delete;

    std::size_t id() const { return id_; }

    bool isConnected() const {
        std::lock_guard<std::mutex> lock(mutex_);
        return sockfd_ >= 0;
    }

    void connectIfNeeded() {
        std::lock_guard<std::mutex> lock(mutex_);
        if (sockfd_ >= 0) {
            return;
        }
        connectLocked();
    }

    void reconnect() {
        std::lock_guard<std::mutex> lock(mutex_);
        closeLocked();
        connectLocked();
    }

    void closeSocket() {
        std::lock_guard<std::mutex> lock(mutex_);
        closeLocked();
    }

    std::string requestLine(const std::string& message) {
        std::lock_guard<std::mutex> lock(mutex_);
        if (sockfd_ < 0) {
            connectLocked();
        }

        try {
            sendAllLocked(message);
            sendAllLocked("\n");
            return recvLineLocked();
        } catch (...) {
            closeLocked();
            throw;
        }
    }

private:
    void connectLocked() {
        int fd = ::socket(AF_INET, SOCK_STREAM, 0);
        if (fd < 0) {
            throwSystemError("socket");
        }

        int one = 1;
        ::setsockopt(fd, SOL_SOCKET, SO_KEEPALIVE, &one, sizeof(one));
        ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_port = htons(endpoint_.port);
        if (::inet_pton(AF_INET, endpoint_.host.c_str(), &addr.sin_addr) != 1) {
            ::close(fd);
            throw SocketError("inet_pton failed for host " + endpoint_.host);
        }

        while (true) {
            if (::connect(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) == 0) {
                break;
            }
            if (errno == EINTR) {
                continue;
            }
            ::close(fd);
            throwSystemError("connect");
        }

        sockfd_ = fd;
    }

    void closeLocked() {
        if (sockfd_ >= 0) {
            ::shutdown(sockfd_, SHUT_RDWR);
            ::close(sockfd_);
            sockfd_ = -1;
        }
    }

    void sendAllLocked(const std::string& data) {
        std::size_t total = 0;
        while (total < data.size()) {
            ssize_t sent = ::send(sockfd_, data.data() + total, data.size() - total, MSG_NOSIGNAL);
            if (sent > 0) {
                total += static_cast<std::size_t>(sent);
                continue;
            }
            if (sent < 0 && errno == EINTR) {
                continue;
            }
            throwSystemError("send");
        }
    }

    std::string recvLineLocked() {
        std::string line;
        char ch = 0;
        while (true) {
            ssize_t n = ::recv(sockfd_, &ch, 1, 0);
            if (n > 0) {
                if (ch == '\n') {
                    return line;
                }
                line.push_back(ch);
                continue;
            }
            if (n == 0) {
                throw SocketError("peer closed connection");
            }
            if (errno == EINTR) {
                continue;
            }
            throwSystemError("recv");
        }
    }

    const std::size_t id_;
    const Endpoint endpoint_;
    mutable std::mutex mutex_;
    int sockfd_;
};

class ConnectionPool {
public:
    ConnectionPool(Endpoint endpoint, std::size_t poolSize) {
        if (poolSize == 0) {
            throw std::invalid_argument("poolSize must be > 0");
        }

        all_.reserve(poolSize);
        for (std::size_t i = 0; i < poolSize; ++i) {
            auto conn = std::make_shared<Connection>(i, endpoint);
            all_.push_back(conn);
            available_.push(conn);
        }
    }

    std::shared_ptr<Connection> acquire() {
        std::unique_lock<std::mutex> lock(mutex_);
        cv_.wait(lock, [&] { return !available_.empty(); });
        auto conn = available_.front();
        available_.pop();
        return conn;
    }

    void release(const std::shared_ptr<Connection>& conn, bool healthy) {
        if (!healthy) {
            conn->closeSocket();
        }

        {
            std::lock_guard<std::mutex> lock(mutex_);
            available_.push(conn);
        }
        cv_.notify_one();
    }

private:
    std::vector<std::shared_ptr<Connection>> all_;
    std::queue<std::shared_ptr<Connection>> available_;
    std::mutex mutex_;
    std::condition_variable cv_;
};

class PooledConnection {
public:
    explicit PooledConnection(ConnectionPool& pool)
        : pool_(pool), conn_(pool_.acquire()), healthy_(true) {}

    ~PooledConnection() {
        if (conn_) {
            pool_.release(conn_, healthy_);
        }
    }

    Connection& operator*() { return *conn_; }
    Connection* operator->() { return conn_.get(); }

    void markUnhealthy() { healthy_ = false; }
    void markHealthy() { healthy_ = true; }

private:
    ConnectionPool& pool_;
    std::shared_ptr<Connection> conn_;
    bool healthy_;
};

class NetworkClient {
public:
    NetworkClient(Endpoint endpoint, std::size_t poolSize, std::size_t maxRetries)
        : pool_(std::move(endpoint), poolSize), maxRetries_(maxRetries) {}

    std::string request(const std::string& payload) {
        PooledConnection pooled(pool_);
        for (std::size_t attempt = 0;; ++attempt) {
            try {
                return pooled->requestLine(payload);
            } catch (...) {
                pooled.markUnhealthy();
                if (attempt >= maxRetries_) {
                    throw;
                }
                pooled->reconnect();
                pooled.markHealthy();
            }
        }
    }

private:
    ConnectionPool pool_;
    std::size_t maxRetries_;
};

class EchoServer {
public:
    explicit EchoServer(uint16_t port)
        : port_(port), listenFd_(-1), running_(false) {}

    ~EchoServer() {
        stop();
    }

    void start() {
        if (running_.exchange(true)) {
            return;
        }

        listenFd_ = ::socket(AF_INET, SOCK_STREAM, 0);
        if (listenFd_ < 0) {
            running_ = false;
            throwSystemError("server socket");
        }

        int one = 1;
        ::setsockopt(listenFd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
        ::setsockopt(listenFd_, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

        sockaddr_in addr{};
        addr.sin_family = AF_INET;
        addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
        addr.sin_port = htons(port_);

        if (::bind(listenFd_, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
            int saved = errno;
            ::close(listenFd_);
            listenFd_ = -1;
            running_ = false;
            errno = saved;
            throwSystemError("bind");
        }

        if (::listen(listenFd_, 128) != 0) {
            int saved = errno;
            ::close(listenFd_);
            listenFd_ = -1;
            running_ = false;
            errno = saved;
            throwSystemError("listen");
        }

        thread_ = std::thread([this] { run(); });
    }

    void stop() {
        if (!running_.exchange(false)) {
            return;
        }

        if (listenFd_ >= 0) {
            ::shutdown(listenFd_, SHUT_RDWR);
            ::close(listenFd_);
            listenFd_ = -1;
        }

        if (thread_.joinable()) {
            thread_.join();
        }
    }

private:
    static void handleClient(int fd) {
        int one = 1;
        ::setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));

        std::string buffer;
        char ch = 0;

        while (true) {
            ssize_t n = ::recv(fd, &ch, 1, 0);
            if (n > 0) {
                if (ch == '\n') {
                    std::string response = "echo:" + buffer + "\n";
                    std::size_t sentTotal = 0;
                    while (sentTotal < response.size()) {
                        ssize_t sent = ::send(fd, response.data() + sentTotal, response.size() - sentTotal, MSG_NOSIGNAL);
                        if (sent > 0) {
                            sentTotal += static_cast<std::size_t>(sent);
                            continue;
                        }
                        if (sent < 0 && errno == EINTR) {
                            continue;
                        }
                        ::shutdown(fd, SHUT_RDWR);
                        ::close(fd);
                        return;
                    }
                    buffer.clear();
                } else {
                    buffer.push_back(ch);
                }
                continue;
            }

            if (n == 0) {
                break;
            }

            if (errno == EINTR) {
                continue;
            }
            break;
        }

        ::shutdown(fd, SHUT_RDWR);
        ::close(fd);
    }

    void run() {
        while (running_) {
            sockaddr_in clientAddr{};
            socklen_t clientLen = sizeof(clientAddr);

            int clientFd = ::accept(listenFd_, reinterpret_cast<sockaddr*>(&clientAddr), &clientLen);
            if (clientFd >= 0) {
                std::thread(&EchoServer::handleClient, clientFd).detach();
                continue;
            }

            if (!running_) {
                break;
            }
            if (errno == EINTR) {
                continue;
            }
        }
    }

    uint16_t port_;
    int listenFd_;
    std::atomic<bool> running_;
    std::thread thread_;
};

int main() {
    try {
        constexpr uint16_t port = 9099;
        EchoServer server(port);
        server.start();

        std::this_thread::sleep_for(std::chrono::milliseconds(100));

        NetworkClient client({ "127.0.0.1", port }, 4, 2);

        std::vector<std::thread> workers;
        std::mutex outputMutex;

        for (int i = 0; i < 8; ++i) {
            workers.emplace_back([i, &client, &outputMutex] {
                for (int j = 0; j < 5; ++j) {
                    std::string payload = "msg-" + std::to_string(i) + "-" + std::to_string(j);
                    std::string reply = client.request(payload);
                    std::lock_guard<std::mutex> lock(outputMutex);
                    std::cout << reply << std::endl;
                }
            });
        }

        for (auto& worker : workers) {
            worker.join();
        }

        server.stop();
        return 0;
    } catch (const std::exception& ex) {
        std::cerr << "fatal: " << ex.what() << std::endl;
        return 1;
    }
}