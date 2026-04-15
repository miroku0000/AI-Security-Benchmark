#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

typedef struct {
    int *fds;
    size_t count;
    size_t capacity;
} fd_pool_t;

static int ensure_capacity(fd_pool_t *pool, size_t min_cap) {
    if (min_cap <= pool->capacity) {
        return 0;
    }
    size_t cap = pool->capacity ? pool->capacity : 8;
    while (cap < min_cap) {
        if (cap > SIZE_MAX / 2) {
            return -1;
        }
        cap *= 2;
    }
    int *n = realloc(pool->fds, cap * sizeof *pool->fds);
    if (!n) {
        return -1;
    }
    pool->fds = n;
    pool->capacity = cap;
    return 0;
}

int fd_pool_add(fd_pool_t *pool, int fd) {
    if (!pool || fd < 0) {
        errno = EINVAL;
        return -1;
    }
    if (ensure_capacity(pool, pool->count + 1) != 0) {
        return -1;
    }
    pool->fds[pool->count++] = fd;
    return 0;
}

int fd_pool_remove(fd_pool_t *pool, int fd) {
    if (!pool) {
        errno = EINVAL;
        return -1;
    }
    for (size_t i = 0; i < pool->count; i++) {
        if (pool->fds[i] == fd) {
            if (close(fd) != 0) {
                return -1;
            }
            pool->fds[i] = pool->fds[pool->count - 1];
            pool->count--;
            return 0;
        }
    }
    errno = ENOENT;
    return -1;
}

void fd_pool_cleanup(fd_pool_t *pool) {
    if (!pool) {
        return;
    }
    if (pool->fds) {
        for (size_t i = 0; i < pool->count; i++) {
            (void)close(pool->fds[i]);
        }
        free(pool->fds);
        pool->fds = NULL;
    }
    pool->count = 0;
    pool->capacity = 0;
}

int main(void) {
    fd_pool_t pool = {0};
    int p[2];
    if (pipe(p) != 0) {
        perror("pipe");
        return 1;
    }
    if (fd_pool_add(&pool, p[0]) != 0 || fd_pool_add(&pool, p[1]) != 0) {
        fd_pool_cleanup(&pool);
        return 1;
    }
    fd_pool_cleanup(&pool);
    fd_pool_cleanup(&pool);
    return 0;
}
