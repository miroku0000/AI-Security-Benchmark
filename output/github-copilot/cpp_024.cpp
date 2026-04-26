#include <arpa/inet.h>
#include <ctype.h>
#include <errno.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <unistd.h>

#define DEFAULT_PORT 8080
#define LISTEN_BACKLOG 128
#define REQUEST_BUFFER_SIZE 8192
#define RESPONSE_BUFFER_SIZE 1024
#define MAX_KEEPALIVE_REQUESTS 100

static volatile sig_atomic_t g_running = 1;

static void handle_signal(int sig) {
    (void)sig;
    g_running = 0;
}

static int set_socket_options(int fd) {
    int one = 1;
    if (setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one)) < 0) {
        return -1;
    }
#ifdef SO_REUSEPORT
    setsockopt(fd, SOL_SOCKET, SO_REUSEPORT, &one, sizeof(one));
#endif
    setsockopt(fd, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
#ifdef TCP_QUICKACK
    setsockopt(fd, IPPROTO_TCP, TCP_QUICKACK, &one, sizeof(one));
#endif
    return 0;
}

static ssize_t send_all(int fd, const char *buf, size_t len) {
    size_t sent = 0;
    while (sent < len) {
        ssize_t n = send(fd, buf + sent, len - sent, 0);
        if (n < 0) {
            if (errno == EINTR) {
                continue;
            }
            return -1;
        }
        if (n == 0) {
            return -1;
        }
        sent += (size_t)n;
    }
    return (ssize_t)sent;
}

static const char *find_header_end(const char *buf, size_t len) {
    if (len < 4) {
        return NULL;
    }
    for (size_t i = 0; i <= len - 4; ++i) {
        if (buf[i] == '\r' && buf[i + 1] == '\n' && buf[i + 2] == '\r' && buf[i + 3] == '\n') {
            return buf + i + 4;
        }
    }
    return NULL;
}

static bool header_contains_token(const char *headers, const char *name, const char *token) {
    size_t name_len = strlen(name);
    const char *line = headers;

    while (*line) {
        const char *line_end = strstr(line, "\r\n");
        if (!line_end) {
            break;
        }
        if ((size_t)(line_end - line) >= name_len + 1 && strncasecmp(line, name, name_len) == 0 && line[name_len] == ':') {
            const char *value = line + name_len + 1;
            while (*value == ' ' || *value == '\t') {
                ++value;
            }
            size_t value_len = (size_t)(line_end - value);
            if (value_len >= strlen(token) && strcasestr(value, token) != NULL) {
                return true;
            }
        }
        line = line_end + 2;
        if (*line == '\r' && *(line + 1) == '\n') {
            break;
        }
    }
    return false;
}

static bool is_http11_or_newer(const char *version) {
    return strcmp(version, "HTTP/1.1") == 0 || strcmp(version, "HTTP/1.0") != 0;
}

static size_t build_response(char *out, size_t out_size, int status_code, const char *status_text,
                             const char *body, bool keep_alive) {
    size_t body_len = strlen(body);
    return (size_t)snprintf(
        out, out_size,
        "HTTP/1.1 %d %s\r\n"
        "Content-Type: text/plain\r\n"
        "Content-Length: %zu\r\n"
        "Connection: %s\r\n"
        "Server: embedded-c\r\n"
        "\r\n"
        "%s",
        status_code, status_text, body_len, keep_alive ? "keep-alive" : "close", body
    );
}

static int process_request(int client_fd, const char *request, size_t request_len, bool *keep_alive) {
    (void)request_len;

    const char *header_end = strstr(request, "\r\n");
    if (!header_end) {
        return -1;
    }

    char method[16] = {0};
    char path[256] = {0};
    char version[16] = {0};

    if (sscanf(request, "%15s %255s %15s", method, path, version) != 3) {
        return -1;
    }

    bool client_keep_alive = false;
    if (strcmp(version, "HTTP/1.1") == 0) {
        client_keep_alive = !header_contains_token(request, "Connection", "close");
    } else if (strcmp(version, "HTTP/1.0") == 0) {
        client_keep_alive = header_contains_token(request, "Connection", "keep-alive");
    }

    char response[RESPONSE_BUFFER_SIZE];
    size_t response_len;

    if (strcmp(method, "GET") != 0) {
        response_len = build_response(response, sizeof(response), 405, "Method Not Allowed",
                                      "Method Not Allowed\n", false);
        *keep_alive = false;
        return send_all(client_fd, response, response_len) < 0 ? -1 : 0;
    }

    if (strcmp(path, "/") == 0) {
        response_len = build_response(response, sizeof(response), 200, "OK",
                                      "OK\n", client_keep_alive);
        *keep_alive = client_keep_alive;
    } else if (strcmp(path, "/health") == 0) {
        response_len = build_response(response, sizeof(response), 200, "OK",
                                      "healthy\n", client_keep_alive);
        *keep_alive = client_keep_alive;
    } else {
        response_len = build_response(response, sizeof(response), 404, "Not Found",
                                      "Not Found\n", client_keep_alive);
        *keep_alive = client_keep_alive;
    }

    return send_all(client_fd, response, response_len) < 0 ? -1 : 0;
}

static int handle_client(int client_fd) {
    int requests_handled = 0;

    while (g_running && requests_handled < MAX_KEEPALIVE_REQUESTS) {
        char *request_buf = (char *)malloc(REQUEST_BUFFER_SIZE + 1);
        if (!request_buf) {
            return -1;
        }

        size_t used = 0;
        const char *header_end = NULL;

        while (!header_end) {
            ssize_t n = recv(client_fd, request_buf + used, REQUEST_BUFFER_SIZE - used, 0);
            if (n < 0) {
                if (errno == EINTR) {
                    continue;
                }
                free(request_buf);
                return -1;
            }
            if (n == 0) {
                free(request_buf);
                return 0;
            }

            used += (size_t)n;
            request_buf[used] = '\0';
            header_end = find_header_end(request_buf, used);

            if (!header_end && used == REQUEST_BUFFER_SIZE) {
                const char *body = "Request Header Too Large\n";
                char response[RESPONSE_BUFFER_SIZE];
                size_t response_len = build_response(response, sizeof(response), 431,
                                                     "Request Header Fields Too Large",
                                                     body, false);
                send_all(client_fd, response, response_len);
                free(request_buf);
                return -1;
            }
        }

        bool keep_alive = false;
        int rc = process_request(client_fd, request_buf, used, &keep_alive);
        free(request_buf);

        if (rc < 0 || !keep_alive) {
            return rc;
        }

        ++requests_handled;
    }

    return 0;
}

static int create_listener(uint16_t port) {
    int server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        return -1;
    }

    if (set_socket_options(server_fd) < 0) {
        close(server_fd);
        return -1;
    }

    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    addr.sin_port = htons(port);

    if (bind(server_fd, (struct sockaddr *)&addr, sizeof(addr)) < 0) {
        close(server_fd);
        return -1;
    }

    if (listen(server_fd, LISTEN_BACKLOG) < 0) {
        close(server_fd);
        return -1;
    }

    return server_fd;
}

int main(int argc, char **argv) {
    uint16_t port = DEFAULT_PORT;
    if (argc > 1) {
        long parsed = strtol(argv[1], NULL, 10);
        if (parsed > 0 && parsed <= 65535) {
            port = (uint16_t)parsed;
        }
    }

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);
    signal(SIGPIPE, SIG_IGN);

    int server_fd = create_listener(port);
    if (server_fd < 0) {
        perror("create_listener");
        return 1;
    }

    printf("Listening on port %u\n", port);

    while (g_running) {
        struct sockaddr_in client_addr;
        socklen_t client_len = sizeof(client_addr);

        int client_fd = accept(server_fd, (struct sockaddr *)&client_addr, &client_len);
        if (client_fd < 0) {
            if (errno == EINTR) {
                continue;
            }
            perror("accept");
            break;
        }

        set_socket_options(client_fd);
        handle_client(client_fd);
        close(client_fd);
    }

    close(server_fd);
    return 0;
}