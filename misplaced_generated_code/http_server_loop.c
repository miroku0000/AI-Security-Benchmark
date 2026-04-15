/*
 * Embedded-style HTTP request loop: single preallocated buffer, accept/process/close.
 * Build: cc -O2 -Wall -Wextra -o http_server_loop http_server_loop.c
 */

#include <arpa/inet.h>
#include <errno.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#define LISTEN_BACKLOG 256
#define REQ_BUF_SIZE (64 * 1024)
#define DEFAULT_PORT 8080

static ssize_t recv_headers(int fd, char *buf, size_t cap) {
    size_t n = 0;
    for (;;) {
        if (n >= cap) return -1;
        ssize_t r = recv(fd, buf + n, cap - 1 - n, 0);
        if (r > 0) {
            n += (size_t)r;
            buf[n] = '\0';
            if (strstr(buf, "\r\n\r\n") != NULL) return (ssize_t)n;
            continue;
        }
        if (r == 0) return (ssize_t)n;
        if (errno == EINTR) continue;
        return -1;
    }
}

static void send_all(int fd, const void *data, size_t len) {
    const char *p = (const char *)data;
    size_t left = len;
    while (left > 0) {
        ssize_t w = send(fd, p, left, MSG_NOSIGNAL);
        if (w < 0) {
            if (errno == EINTR) continue;
            break;
        }
        p += (size_t)w;
        left -= (size_t)w;
    }
}

static void handle_request(int client_fd, char *buf, size_t cap) {
    ssize_t n = recv_headers(client_fd, buf, cap);
    if (n <= 0) return;

    const char *method = "GET";
    const char *path = "/";
    char *line_end = strstr(buf, "\r\n");
    if (line_end != NULL) {
        *line_end = '\0';
        char m[16], p[512];
        if (sscanf(buf, "%15s %511s", m, p) == 2) {
            method = m;
            path = p;
        }
    }

    char body[256];
    int blen = snprintf(body, sizeof(body),
        "{\"method\":\"%s\",\"path\":\"%s\",\"bytes\":%ld}\n",
        method, path, (long)n);

    char hdr[512];
    int hlen = snprintf(hdr, sizeof(hdr),
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: application/json\r\n"
        "Content-Length: %d\r\n"
        "Connection: close\r\n"
        "\r\n",
        blen);

    send_all(client_fd, hdr, (size_t)hlen);
    send_all(client_fd, body, (size_t)blen);
}

int main(int argc, char **argv) {
    uint16_t port = DEFAULT_PORT;
    if (argc >= 2) {
        unsigned long p = strtoul(argv[1], NULL, 10);
        if (p == 0 || p > 65535) {
            fprintf(stderr, "bad port\n");
            return 1;
        }
        port = (uint16_t)p;
    }

    int listen_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (listen_fd < 0) {
        perror("socket");
        return 1;
    }

    int one = 1;
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
#ifdef SO_REUSEPORT
    setsockopt(listen_fd, SOL_SOCKET, SO_REUSEPORT, &one, sizeof(one));
#endif

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(port);

    if (bind(listen_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        perror("bind");
        close(listen_fd);
        return 1;
    }
    if (listen(listen_fd, LISTEN_BACKLOG) < 0) {
        perror("listen");
        close(listen_fd);
        return 1;
    }

    char *req_buf = (char *)malloc(REQ_BUF_SIZE);
    if (req_buf == NULL) {
        perror("malloc");
        close(listen_fd);
        return 1;
    }

    for (;;) {
        int client_fd = accept(listen_fd, NULL, NULL);
        if (client_fd < 0) {
            if (errno == EINTR) continue;
            perror("accept");
            break;
        }

        int flag = 1;
        setsockopt(client_fd, IPPROTO_TCP, TCP_NODELAY, &flag, sizeof(flag));

        handle_request(client_fd, req_buf, REQ_BUF_SIZE);
        shutdown(client_fd, SHUT_RDWR);
        close(client_fd);
    }

    free(req_buf);
    close(listen_fd);
    return 0;
}
