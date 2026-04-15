#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <pthread.h>
#include <signal.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/epoll.h>
#include <sys/time.h>

#define PORT 8080
#define BUFFER_SIZE 8192
#define MAX_CLIENTS 1000
#define MAX_EVENTS 64
#define REQUEST_POOL_SIZE 100
#define RESPONSE_HEADER "HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: %zu\r\n\r\n"

typedef struct {
    char *buffer;
    size_t size;
    size_t used;
    int client_fd;
    struct timeval start_time;
} request_buffer_t;

typedef struct {
    request_buffer_t *buffers;
    int *free_list;
    int free_count;
    pthread_mutex_t lock;
} buffer_pool_t;

static buffer_pool_t pool;
static int server_fd;
static int epoll_fd;
static volatile int running = 1;

void signal_handler(int sig) {
    running = 0;
}

void init_buffer_pool() {
    pool.buffers = malloc(REQUEST_POOL_SIZE * sizeof(request_buffer_t));
    pool.free_list = malloc(REQUEST_POOL_SIZE * sizeof(int));
    
    for (int i = 0; i < REQUEST_POOL_SIZE; i++) {
        pool.buffers[i].buffer = malloc(BUFFER_SIZE);
        pool.buffers[i].size = BUFFER_SIZE;
        pool.buffers[i].used = 0;
        pool.buffers[i].client_fd = -1;
        pool.free_list[i] = i;
    }
    
    pool.free_count = REQUEST_POOL_SIZE;
    pthread_mutex_init(&pool.lock, NULL);
}

request_buffer_t* acquire_buffer() {
    pthread_mutex_lock(&pool.lock);
    if (pool.free_count == 0) {
        pthread_mutex_unlock(&pool.lock);
        return NULL;
    }
    
    int idx = pool.free_list[--pool.free_count];
    request_buffer_t *buf = &pool.buffers[idx];
    buf->used = 0;
    gettimeofday(&buf->start_time, NULL);
    pthread_mutex_unlock(&pool.lock);
    
    return buf;
}

void release_buffer(request_buffer_t *buf) {
    if (!buf) return;
    
    pthread_mutex_lock(&pool.lock);
    int idx = buf - pool.buffers;
    if (idx >= 0 && idx < REQUEST_POOL_SIZE) {
        buf->client_fd = -1;
        pool.free_list[pool.free_count++] = idx;
    }
    pthread_mutex_unlock(&pool.lock);
}

void destroy_buffer_pool() {
    for (int i = 0; i < REQUEST_POOL_SIZE; i++) {
        free(pool.buffers[i].buffer);
    }
    free(pool.buffers);
    free(pool.free_list);
    pthread_mutex_destroy(&pool.lock);
}

int set_nonblocking(int fd) {
    int flags = fcntl(fd, F_GETFL, 0);
    if (flags == -1) return -1;
    return fcntl(fd, F_SETFL, flags | O_NONBLOCK);
}

void process_request(request_buffer_t *req) {
    char *method = NULL;
    char *path = NULL;
    char *version = NULL;
    
    char *line_end = strstr(req->buffer, "\r\n");
    if (line_end) {
        *line_end = '\0';
        
        method = strtok(req->buffer, " ");
        path = strtok(NULL, " ");
        version = strtok(NULL, " ");
    }
    
    const char *response_body = "OK";
    char response_header[256];
    
    if (method && strcmp(method, "GET") == 0 && path) {
        snprintf(response_header, sizeof(response_header), RESPONSE_HEADER, strlen(response_body));
    } else {
        snprintf(response_header, sizeof(response_header), 
                "HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n");
        response_body = "";
    }
    
    send(req->client_fd, response_header, strlen(response_header), MSG_NOSIGNAL);
    if (strlen(response_body) > 0) {
        send(req->client_fd, response_body, strlen(response_body), MSG_NOSIGNAL);
    }
    
    struct timeval end_time;
    gettimeofday(&end_time, NULL);
    long elapsed = (end_time.tv_sec - req->start_time.tv_sec) * 1000000 + 
                   (end_time.tv_usec - req->start_time.tv_usec);
    
    if (elapsed > 100000) {
        printf("Slow request: %ld us\n", elapsed);
    }
}

void handle_client(int client_fd) {
    request_buffer_t *req = acquire_buffer();
    if (!req) {
        close(client_fd);
        return;
    }
    
    req->client_fd = client_fd;
    
    ssize_t bytes = recv(client_fd, req->buffer, req->size - 1, 0);
    
    if (bytes > 0) {
        req->buffer[bytes] = '\0';
        req->used = bytes;
        
        if (strstr(req->buffer, "\r\n\r\n") || strstr(req->buffer, "\n\n")) {
            process_request(req);
        }
    }
    
    close(client_fd);
    release_buffer(req);
}

int init_server() {
    server_fd = socket(AF_INET, SOCK_STREAM, 0);
    if (server_fd < 0) {
        perror("socket");
        return -1;
    }
    
    int opt = 1;
    if (setsockopt(server_fd, SOL_SOCKET, SO_REUSEADDR, &opt, sizeof(opt)) < 0) {
        perror("setsockopt");
        return -1;
    }
    
    struct sockaddr_in addr;
    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = INADDR_ANY;
    addr.sin_port = htons(PORT);
    
    if (bind(server_fd, (struct sockaddr*)&addr, sizeof(addr)) < 0) {
        perror("bind");
        return -1;
    }
    
    if (listen(server_fd, MAX_CLIENTS) < 0) {
        perror("listen");
        return -1;
    }
    
    set_nonblocking(server_fd);
    
    epoll_fd = epoll_create1(0);
    if (epoll_fd < 0) {
        perror("epoll_create1");
        return -1;
    }
    
    struct epoll_event ev;
    ev.events = EPOLLIN;
    ev.data.fd = server_fd;
    
    if (epoll_ctl(epoll_fd, EPOLL_CTL_ADD, server_fd, &ev) < 0) {
        perror("epoll_ctl");
        return -1;
    }
    
    return 0;
}

void run_server() {
    struct epoll_event events[MAX_EVENTS];
    
    printf("Server listening on port %d\n", PORT);
    
    while (running) {
        int nfds = epoll_wait(epoll_fd, events, MAX_EVENTS, 1000);
        
        if (nfds < 0) {
            if (errno == EINTR) continue;
            perror("epoll_wait");
            break;
        }
        
        for (int i = 0; i < nfds; i++) {
            if (events[i].data.fd == server_fd) {
                while (1) {
                    struct sockaddr_in client_addr;
                    socklen_t client_len = sizeof(client_addr);
                    
                    int client_fd = accept(server_fd, (struct sockaddr*)&client_addr, &client_len);
                    if (client_fd < 0) {
                        if (errno == EAGAIN || errno == EWOULDBLOCK) {
                            break;
                        }
                        perror("accept");
                        continue;
                    }
                    
                    set_nonblocking(client_fd);
                    handle_client(client_fd);
                }
            }
        }
    }
}

int main() {
    signal(SIGINT, signal_handler);
    signal(SIGTERM, signal_handler);
    signal(SIGPIPE, SIG_IGN);
    
    init_buffer_pool();
    
    if (init_server() < 0) {
        destroy_buffer_pool();
        return 1;
    }
    
    run_server();
    
    close(epoll_fd);
    close(server_fd);
    destroy_buffer_pool();
    
    printf("\nServer shut down\n");
    return 0;
}