while (total < capacity) {
        ssize_t n = read(fd, buffer + total, capacity - total);
        if (n > 0) {
            total += (size_t)n;
            continue;
        }
        if (n == 0) {
            break;
        }
        if (errno == EINTR) {
            continue;
        }
        free(buffer);
        close_preserve_errno(fd);
        return NULL;
    }