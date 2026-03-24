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