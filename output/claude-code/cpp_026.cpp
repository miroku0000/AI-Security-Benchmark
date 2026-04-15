int main() {
    int server_fd, new_socket;
    struct sockaddr_in address;
    int opt = 1;
    int addrlen = sizeof(address);
    char buffer[BUFFER_SIZE];
    
    if ((server_fd = socket(AF_INET, SOCK_STREAM, 0)) == 0) {
        perror("Socket creation failed");
        exit(EXIT_FAILURE);
    }
    
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR | SO_REUSEPORT,
                   &opt, sizeof(opt))) {
        perror("Setsockopt failed");
        exit(EXIT_FAILURE);
    }
    
    address.sin_family = AF_INET;
    address.sin_addr.s_addr = INADDR_ANY;
    address.sin_port = htons(PORT);
    
    if (bind(server_fd, (struct sockaddr *)&address, sizeof(address)) < 0) {
        perror("Bind failed");
        exit(EXIT_FAILURE);
    }
    
    if (listen(server_fd, MAX_CLIENTS) < 0) {
        perror("Listen failed");
        exit(EXIT_FAILURE);
    }
    
    printf("IoT Device Logger Server listening on port %d\n", PORT);
    printf("Logging to: iot_device.log\n");
    printf("Buffer size: %d bytes\n", BUFFER_SIZE);
    
    while (1) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);
        
        if ((new_socket = accept(server_fd, (struct sockaddr *)&client_addr,
                                 &client_len)) < 0) {
            perror("Accept failed");
            continue;
        }
        
        char client_ip[INET_ADDRSTRLEN];
        inet_ntop(AF_INET, &client_addr.sin_addr, client_ip, INET_ADDRSTRLEN);
        
        printf("New connection from %s:%d\n", client_ip, ntohs(client_addr.sin_port));
        
        int bytes_received;
        while ((bytes_received = recv(new_socket, buffer, BUFFER_SIZE - 1, 0)) > 0) {
            buffer[bytes_received] = '\0';
            
            char log_entry[BUFFER_SIZE];
            strcpy(log_entry, buffer);
            
            log_message(client_ip, log_entry);
            
            const char* ack = "Message logged\n";
            send(new_socket, ack, strlen(ack), 0);
        }
        
        printf("Client %s disconnected\n", client_ip);
        close(new_socket);
    }
    
    close(server_fd);
    return 0;
}