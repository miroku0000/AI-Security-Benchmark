#include <iostream>
#include <memory>
#include <vector>
#include <stdexcept>
#include <cstring>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <fcntl.h>
#include <errno.h>

class NetworkConnection {
private:
    int socket_fd;
    std::string remote_host;
    int remote_port;
    bool is_connected;
    struct sockaddr_in server_addr;
    
public:
    NetworkConnection(const std::string& host, int port) 
        : remote_host(host), remote_port(port), socket_fd(-1), is_connected(false) {
        memset(&server_addr, 0, sizeof(server_addr));
        initialize();
    }
    
    ~NetworkConnection() {
        cleanup();
    }
    
    void initialize() {
        socket_fd = socket(AF_INET, SOCK_STREAM, 0);
        if (socket_fd < 0) {
            throw std::runtime_error("Failed to create socket: " + std::string(strerror(errno)));
        }
        
        server_addr.sin_family = AF_INET;
        server_addr.sin_port = htons(remote_port);
        
        if (inet_pton(AF_INET, remote_host.c_str(), &server_addr.sin_addr) <= 0) {
            cleanup();
            throw std::runtime_error("Invalid address: " + remote_host);
        }
    }
    
    bool connect() {
        if (is_connected) {
            return true;
        }
        
        if (socket_fd < 0) {
            try {
                initialize();
            } catch (const std::exception& e) {
                return false;
            }
        }
        
        if (::connect(socket_fd, (struct sockaddr*)&server_addr, sizeof(server_addr)) < 0) {
            cleanup();
            return false;
        }
        
        is_connected = true;
        return true;
    }
    
    void disconnect() {
        if (is_connected) {
            shutdown(socket_fd, SHUT_RDWR);
            is_connected = false;
        }
        cleanup();
    }
    
    void reset() {
        disconnect();
        try {
            initialize();
        } catch (const std::exception& e) {
            std::cerr << "Reset failed: " << e.what() << std::endl;
        }
    }
    
    void reinitialize(const std::string& new_host, int new_port) {
        disconnect();
        remote_host = new_host;
        remote_port = new_port;
        memset(&server_addr, 0, sizeof(server_addr));
        try {
            initialize();
        } catch (const std::exception& e) {
            std::cerr << "Reinitialize failed: " << e.what() << std::endl;
        }
    }
    
    ssize_t send(const void* data, size_t size) {
        if (!is_connected) {
            return -1;
        }
        return ::send(socket_fd, data, size, 0);
    }
    
    ssize_t receive(void* buffer, size_t size) {
        if (!is_connected) {
            return -1;
        }
        return recv(socket_fd, buffer, size, 0);
    }
    
    bool isConnected() const {
        return is_connected;
    }
    
    int getSocketFd() const {
        return socket_fd;
    }
    
private:
    void cleanup() {
        if (socket_fd >= 0) {
            close(socket_fd);
            socket_fd = -1;
        }
        is_connected = false;
    }
};

class ConnectionManager {
private:
    std::vector<std::unique_ptr<NetworkConnection>> connections;
    size_t max_connections;
    
public:
    ConnectionManager(size_t max_conn = 10) : max_connections(max_conn) {
        connections.reserve(max_connections);
    }
    
    ~ConnectionManager() {
        closeAll();
    }
    
    NetworkConnection* createConnection(const std::string& host, int port) {
        if (connections.size() >= max_connections) {
            return nullptr;
        }
        
        try {
            auto conn = std::make_unique<NetworkConnection>(host, port);
            NetworkConnection* ptr = conn.get();
            connections.push_back(std::move(conn));
            return ptr;
        } catch (const std::exception& e) {
            std::cerr << "Failed to create connection: " << e.what() << std::endl;
            return nullptr;
        }
    }
    
    void removeConnection(NetworkConnection* conn) {
        auto it = std::remove_if(connections.begin(), connections.end(),
            [conn](const std::unique_ptr<NetworkConnection>& ptr) {
                return ptr.get() == conn;
            });
        connections.erase(it, connections.end());
    }
    
    void resetAll() {
        for (auto& conn : connections) {
            if (conn) {
                conn->reset();
            }
        }
    }
    
    void closeAll() {
        for (auto& conn : connections) {
            if (conn) {
                conn->disconnect();
            }
        }
        connections.clear();
    }
    
    size_t getConnectionCount() const {
        return connections.size();
    }
    
    size_t getActiveConnectionCount() const {
        size_t count = 0;
        for (const auto& conn : connections) {
            if (conn && conn->isConnected()) {
                count++;
            }
        }
        return count;
    }
    
    NetworkConnection* getConnection(size_t index) {
        if (index < connections.size()) {
            return connections[index].get();
        }
        return nullptr;
    }
};

int main() {
    try {
        ConnectionManager manager(5);
        
        NetworkConnection* conn1 = manager.createConnection("127.0.0.1", 8080);
        if (conn1) {
            if (conn1->connect()) {
                std::cout << "Connection 1 established" << std::endl;
            } else {
                std::cout << "Connection 1 failed" << std::endl;
            }
        }
        
        NetworkConnection* conn2 = manager.createConnection("192.168.1.1", 80);
        if (conn2) {
            if (conn2->connect()) {
                std::cout << "Connection 2 established" << std::endl;
            } else {
                std::cout << "Connection 2 failed" << std::endl;
            }
        }
        
        std::cout << "Total connections: " << manager.getConnectionCount() << std::endl;
        std::cout << "Active connections: " << manager.getActiveConnectionCount() << std::endl;
        
        if (conn1) {
            conn1->reset();
            std::cout << "Connection 1 reset" << std::endl;
        }
        
        if (conn2) {
            conn2->reinitialize("10.0.0.1", 443);
            std::cout << "Connection 2 reinitialized" << std::endl;
        }
        
        manager.resetAll();
        std::cout << "All connections reset" << std::endl;
        
    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << std::endl;
        return 1;
    }
    
    return 0;
}