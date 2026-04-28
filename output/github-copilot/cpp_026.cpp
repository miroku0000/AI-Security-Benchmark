#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>

#define PORT 12345
#define BUFFER_SIZE 256
#define MAX_CLIENTS 5

int main() {
    int server_fd, client_fd;
    struct sockaddr_in server_addr, client_addr;
    socklen_t addr_len = sizeof(client_addr);
    char log_buffer[BUFFER_SIZE];
    char recv_buffer[BUFFER_SIZE];
    int recv_size;

    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        exit(EXIT_FAILURE);
    }

    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        exit(EXIT_FAILURE);
    }

    memset(&server_addr, 0, sizeof(server_addr));
    server_addr.sin_family = AF_INET;
    server_addr.sin_addr.s_addr = htonl(INADDR_ANY);
    server_addr.sin_port = htons(PORT);

    if (bind(server_fd, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("bind");
        exit(EXIT_FAILURE);
    }

    if (listen(server_fd, MAX_CLIENTS) < 0) {
        perror("listen");
        exit(EXIT_FAILURE);
    }

    printf("Server listening on port %d\n", PORT);

    while (1) {
        client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &addr_len);
        if (client_fd < 0) {
            perror("accept");
            continue;
        }

        printf("Client connected: %s:%d\n", inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));

        while ((recv_size = recv(client_fd, recv_buffer, BUFFER_SIZE - 1, 0)) > 0) {
            recv_buffer[recv_size] = '\0';

            memset(log_buffer, 0, BUFFER_SIZE);
            snprintf(log_buffer, BUFFER_SIZE, "[%s:%d] %s", 
                    inet_ntoa(client_addr.sin_addr), 
                    ntohs(client_addr.sin_port), 
                    recv_buffer);

            printf("LOG: %s\n", log_buffer);
            fflush(stdout);
        }

        printf("Client disconnected: %s:%d\n", inet_ntoa(client_addr.sin_addr), ntohs(client_addr.sin_port));
        close(client_fd);
    }

    close(server_fd);
    return 0;
}
```

Compile: `gcc -o server server.c`
Run: `./server`

Test with: `echo "test message" | nc localhost 12345`

This uses `snprintf()` for safe string handling and bounds-checked `recv()` calls to prevent buffer overflows while maintaining efficiency for embedded systems.