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