#include <iostream>
#include <vector>
#include <memory>
#include <mutex>
#include <thread>
#include <chrono>
#include <queue>
#include <condition_variable>
#include <atomic>
#include <cstring>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>

class Connection {
private:
    int socket_fd;
    std::string host;
    int port;
    bool connected;
    std::atomic<bool> in_use;
    std::chrono::steady_clock::time_point last_used;
    int retry_count;
    static const int MAX_RETRIES = 3;
    static const int RETRY_DELAY_MS = 1000;

public:
    Connection(const std::string& host, int port) 
        : socket_fd(-1), host(host), port(port), connected(false), in_use(false), retry_count(0) {}
    
    ~Connection() {
        disconnect();
    }

    bool connect() {
        if (connected) return true;
        
        socket_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (socket_fd < 0) {
            return false;
        }

        int flags = fcntl(socket_fd, F_GETFL, 0);
        fcntl(socket_fd, F_SETFL, flags | O_NONBLOCK);

        struct sockaddr_in server_addr;
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(port);
        inet_pton(AF_INET, host.c_str(), &server_addr.sin_addr);

        int result = ::connect(socket_fd, (struct sockaddr*)&server_addr, sizeof(server_addr));
        
        if (result < 0 && errno != EINPROGRESS) {
            close(socket_fd);
            socket_fd = -1;
            return false;
        }

        fd_set write_fds;
        FD_ZERO(&write_fds);
        FD_SET(socket_fd, &write_fds);
        
        struct timeval timeout;
        timeout.tv_sec = 5;
        timeout.tv_usec = 0;
        
        result = select(socket_fd + 1, nullptr, &write_fds, nullptr, &timeout);
        
        if (result <= 0) {
            close(socket_fd);
            socket_fd = -1;
            return false;
        }

        int error = 0;
        socklen_t error_len = sizeof(error);
        getsockopt(socket_fd, SOL_SOCKET, SO_ERROR, &error, &error_len);
        
        if (error != 0) {
            close(socket_fd);
            socket_fd = -1;
            return false;
        }

        connected = true;
        retry_count = 0;
        return true;
    }

    bool reconnect() {
        disconnect();
        
        for (int i = 0; i < MAX_RETRIES; i++) {
            if (connect()) {
                return true;
            }
            std::this_thread::sleep_for(std::chrono::milliseconds(RETRY_DELAY_MS * (i + 1)));
            retry_count++;
        }
        
        return false;
    }

    void disconnect() {
        if (socket_fd >= 0) {
            close(socket_fd);
            socket_fd = -1;
        }
        connected = false;
    }

    bool send(const void* data, size_t size) {
        if (!connected) {
            if (!reconnect()) {
                return false;
            }
        }

        size_t total_sent = 0;
        const char* buffer = static_cast<const char*>(data);
        
        while (total_sent < size) {
            int sent = ::send(socket_fd, buffer + total_sent, size - total_sent, MSG_NOSIGNAL);
            
            if (sent < 0) {
                if (errno == EAGAIN || errno == EWOULDBLOCK) {
                    std::this_thread::sleep_for(std::chrono::milliseconds(10));
                    continue;
                }
                connected = false;
                return false;
            }
            
            total_sent += sent;
        }
        
        return true;
    }

    int receive(void* buffer, size_t buffer_size) {
        if (!connected) {
            if (!reconnect()) {
                return -1;
            }
        }

        int received = ::recv(socket_fd, buffer, buffer_size, 0);
        
        if (received < 0) {
            if (errno != EAGAIN && errno != EWOULDBLOCK) {
                connected = false;
            }
            return -1;
        }
        
        if (received == 0) {
            connected = false;
            return -1;
        }
        
        return received;
    }

    bool isConnected() const { return connected; }
    bool isInUse() const { return in_use.load(); }
    void setInUse(bool use) { in_use.store(use); }
    void updateLastUsed() { last_used = std::chrono::steady_clock::now(); }
    std::chrono::steady_clock::time_point getLastUsed() const { return last_used; }
    int getRetryCount() const { return retry_count; }
};

class ConnectionPool {
private:
    std::vector<std::unique_ptr<Connection>> connections;
    std::queue<Connection*> available_connections;
    std::mutex pool_mutex;
    std::condition_variable pool_cv;
    std::string host;
    int port;
    size_t max_connections;
    size_t current_connections;
    std::atomic<bool> running;
    std::thread cleanup_thread;
    static const int IDLE_TIMEOUT_SECONDS = 300;
    static const int CLEANUP_INTERVAL_SECONDS = 60;

public:
    ConnectionPool(const std::string& host, int port, size_t max_connections)
        : host(host), port(port), max_connections(max_connections), 
          current_connections(0), running(true) {
        
        cleanup_thread = std::thread(&ConnectionPool::cleanupIdleConnections, this);
    }

    ~ConnectionPool() {
        running = false;
        pool_cv.notify_all();
        
        if (cleanup_thread.joinable()) {
            cleanup_thread.join();
        }
        
        std::lock_guard<std::mutex> lock(pool_mutex);
        connections.clear();
    }

    Connection* acquire() {
        std::unique_lock<std::mutex> lock(pool_mutex);
        
        while (available_connections.empty() && current_connections >= max_connections) {
            pool_cv.wait(lock);
        }
        
        if (!available_connections.empty()) {
            Connection* conn = available_connections.front();
            available_connections.pop();
            conn->setInUse(true);
            conn->updateLastUsed();
            
            if (!conn->isConnected()) {
                if (!conn->reconnect()) {
                    releaseConnection(conn, true);
                    return acquire();
                }
            }
            
            return conn;
        }
        
        if (current_connections < max_connections) {
            auto new_conn = std::make_unique<Connection>(host, port);
            
            if (new_conn->connect()) {
                Connection* conn_ptr = new_conn.get();
                connections.push_back(std::move(new_conn));
                current_connections++;
                conn_ptr->setInUse(true);
                conn_ptr->updateLastUsed();
                return conn_ptr;
            }
        }
        
        return nullptr;
    }

    void release(Connection* conn) {
        if (!conn) return;
        releaseConnection(conn, false);
    }

    void releaseWithError(Connection* conn) {
        if (!conn) return;
        releaseConnection(conn, true);
    }

    bool sendData(const void* data, size_t size) {
        Connection* conn = acquire();
        if (!conn) return false;
        
        bool success = conn->send(data, size);
        
        if (!success) {
            if (conn->reconnect()) {
                success = conn->send(data, size);
            }
        }
        
        if (success) {
            release(conn);
        } else {
            releaseWithError(conn);
        }
        
        return success;
    }

    int receiveData(void* buffer, size_t buffer_size) {
        Connection* conn = acquire();
        if (!conn) return -1;
        
        int received = conn->receive(buffer, buffer_size);
        
        if (received < 0) {
            if (conn->reconnect()) {
                received = conn->receive(buffer, buffer_size);
            }
        }
        
        if (received >= 0) {
            release(conn);
        } else {
            releaseWithError(conn);
        }
        
        return received;
    }

    size_t getActiveConnections() const {
        std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(pool_mutex));
        return current_connections;
    }

    size_t getAvailableConnections() const {
        std::lock_guard<std::mutex> lock(const_cast<std::mutex&>(pool_mutex));
        return available_connections.size();
    }

private:
    void releaseConnection(Connection* conn, bool has_error) {
        std::lock_guard<std::mutex> lock(pool_mutex);
        
        conn->setInUse(false);
        
        if (has_error) {
            conn->disconnect();
            
            for (auto it = connections.begin(); it != connections.end(); ++it) {
                if (it->get() == conn) {
                    connections.erase(it);
                    current_connections--;
                    break;
                }
            }
        } else {
            conn->updateLastUsed();
            available_connections.push(conn);
        }
        
        pool_cv.notify_one();
    }

    void cleanupIdleConnections() {
        while (running) {
            std::this_thread::sleep_for(std::chrono::seconds(CLEANUP_INTERVAL_SECONDS));
            
            std::lock_guard<std::mutex> lock(pool_mutex);
            
            auto now = std::chrono::steady_clock::now();
            std::vector<Connection*> to_remove;
            
            std::queue<Connection*> temp_queue;
            while (!available_connections.empty()) {
                Connection* conn = available_connections.front();
                available_connections.pop();
                
                auto idle_time = std::chrono::duration_cast<std::chrono::seconds>(
                    now - conn->getLastUsed()).count();
                
                if (idle_time > IDLE_TIMEOUT_SECONDS) {
                    to_remove.push_back(conn);
                } else {
                    temp_queue.push(conn);
                }
            }
            
            available_connections = temp_queue;
            
            for (auto* conn : to_remove) {
                for (auto it = connections.begin(); it != connections.end(); ++it) {
                    if (it->get() == conn) {
                        connections.erase(it);
                        current_connections--;
                        break;
                    }
                }
            }
        }
    }
};

class NetworkClient {
private:
    std::unique_ptr<ConnectionPool> pool;
    std::string server_host;
    int server_port;
    size_t pool_size;
    std::atomic<bool> initialized;

public:
    NetworkClient(const std::string& host, int port, size_t pool_size = 10)
        : server_host(host), server_port(port), pool_size(pool_size), initialized(false) {}

    bool initialize() {
        if (initialized.load()) return true;
        
        try {
            pool = std::make_unique<ConnectionPool>(server_host, server_port, pool_size);
            initialized.store(true);
            return true;
        } catch (...) {
            return false;
        }
    }

    void shutdown() {
        if (initialized.load()) {
            pool.reset();
            initialized.store(false);
        }
    }

    bool send(const std::string& message) {
        if (!initialized.load()) return false;
        return pool->sendData(message.c_str(), message.size());
    }

    bool send(const void* data, size_t size) {
        if (!initialized.load()) return false;
        return pool->sendData(data, size);
    }

    std::string receive(size_t max_size = 4096) {
        if (!initialized.load()) return "";
        
        std::vector<char> buffer(max_size);
        int received = pool->receiveData(buffer.data(), max_size);
        
        if (received > 0) {
            return std::string(buffer.data(), received);
        }
        
        return "";
    }

    int receive(void* buffer, size_t buffer_size) {
        if (!initialized.load()) return -1;
        return pool->receiveData(buffer, buffer_size);
    }

    bool executeRequest(const void* request_data, size_t request_size,
                       void* response_buffer, size_t response_buffer_size,
                       int& response_size) {
        Connection* conn = pool->acquire();
        if (!conn) return false;
        
        bool success = conn->send(request_data, request_size);
        
        if (!success && conn->reconnect()) {
            success = conn->send(request_data, request_size);
        }
        
        if (success) {
            response_size = conn->receive(response_buffer, response_buffer_size);
            
            if (response_size < 0 && conn->reconnect()) {
                if (conn->send(request_data, request_size)) {
                    response_size = conn->receive(response_buffer, response_buffer_size);
                }
            }
        }
        
        if (response_size >= 0) {
            pool->release(conn);
            return true;
        } else {
            pool->releaseWithError(conn);
            return false;
        }
    }

    size_t getActiveConnections() const {
        if (!initialized.load()) return 0;
        return pool->getActiveConnections();
    }

    size_t getAvailableConnections() const {
        if (!initialized.load()) return 0;
        return pool->getAvailableConnections();
    }
};

int main() {
    NetworkClient client("127.0.0.1", 8080, 5);
    
    if (!client.initialize()) {
        std::cerr << "Failed to initialize client" << std::endl;
        return 1;
    }
    
    std::string message = "Hello, Server!";
    if (client.send(message)) {
        std::cout << "Message sent successfully" << std::endl;
        
        std::string response = client.receive();
        if (!response.empty()) {
            std::cout << "Received: " << response << std::endl;
        }
    }
    
    std::cout << "Active connections: " << client.getActiveConnections() << std::endl;
    std::cout << "Available connections: " << client.getAvailableConnections() << std::endl;
    
    client.shutdown();
    
    return 0;
}