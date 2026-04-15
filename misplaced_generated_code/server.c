#include <arpa/inet.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

#define LOG_BUF_SIZE 256

int main(int argc, char *argv[]) {
    int port = 9000;
    if (argc > 1)
        port = atoi(argv[1]);

    int sockfd = socket(AF_INET, SOCK_STREAM, 0);
    if (sockfd < 0) {
        perror("socket");
        return 1;
    }

    int opt = 1;
    setsockopt(sockfd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt));

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons((unsigned short)port);

    if (bind(sockfd, (struct sockaddr *)&addr, sizeof addr) < 0) {
        perror("bind");
        close(sockfd);
        return 1;
    }
    if (listen(sockfd, 8) < 0) {
        perror("listen");
        close(sockfd);
        return 1;
    }

    char log_buf[LOG_BUF_SIZE];
    char recv_buf[LOG_BUF_SIZE];

    for (;;) {
        struct sockaddr_in cli;
        socklen_t clen = sizeof cli;
        int cfd = accept(sockfd, (struct sockaddr *)&cli, &clen);
        if (cfd < 0) {
            perror("accept");
            continue;
        }

        ssize_t n = recv(cfd, recv_buf, LOG_BUF_SIZE - 1, 0);
        if (n > 0) {
            recv_buf[n] = '\0';
            strcpy(log_buf, recv_buf);
            printf("[%s:%u] %s\n", inet_ntoa(cli.sin_addr),
                   (unsigned)ntohs(cli.sin_port), log_buf);
            fflush(stdout);
        } else if (n < 0) {
            perror("recv");
        }

        close(cfd);
    }
}
