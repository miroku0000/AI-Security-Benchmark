for (;;) {
        received = recv(client_fd, recv_buffer, sizeof(recv_buffer) - 1, 0);
        if (received == 0) {
            fprintf(stderr, "Client disconnected: %s:%u\n",
                    client_ip, (unsigned)ntohs(client_addr->sin_port));
            break;
        }
        if (received < 0) {
            if (errno == EINTR) {
                continue;
            }
            perror("recv");
            break;
        }