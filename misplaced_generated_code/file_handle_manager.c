#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <string.h>
#include <fcntl.h>
#include <errno.h>

#define MAX_HANDLES 1024
#define INVALID_FD -1

typedef struct FileHandle {
    int fd;
    char *filename;
    int flags;
    int in_use;
} FileHandle;

typedef struct FileHandlePool {
    FileHandle *handles;
    int capacity;
    int count;
    int initialized;
} FileHandlePool;

static FileHandlePool g_pool = {NULL, 0, 0, 0};

int init_pool(int capacity) {
    if (g_pool.initialized) {
        return 0;
    }
    
    if (capacity <= 0 || capacity > MAX_HANDLES) {
        capacity = MAX_HANDLES;
    }
    
    g_pool.handles = (FileHandle *)calloc(capacity, sizeof(FileHandle));
    if (!g_pool.handles) {
        return -1;
    }
    
    for (int i = 0; i < capacity; i++) {
        g_pool.handles[i].fd = INVALID_FD;
        g_pool.handles[i].filename = NULL;
        g_pool.handles[i].flags = 0;
        g_pool.handles[i].in_use = 0;
    }
    
    g_pool.capacity = capacity;
    g_pool.count = 0;
    g_pool.initialized = 1;
    
    return 0;
}

int add_handle(const char *filename, int flags) {
    if (!g_pool.initialized) {
        if (init_pool(MAX_HANDLES) < 0) {
            return INVALID_FD;
        }
    }
    
    if (!filename) {
        return INVALID_FD;
    }
    
    if (g_pool.count >= g_pool.capacity) {
        return INVALID_FD;
    }
    
    int fd = open(filename, flags, 0644);
    if (fd < 0) {
        return INVALID_FD;
    }
    
    int slot = -1;
    for (int i = 0; i < g_pool.capacity; i++) {
        if (!g_pool.handles[i].in_use) {
            slot = i;
            break;
        }
    }
    
    if (slot < 0) {
        close(fd);
        return INVALID_FD;
    }
    
    g_pool.handles[slot].fd = fd;
    g_pool.handles[slot].filename = strdup(filename);
    g_pool.handles[slot].flags = flags;
    g_pool.handles[slot].in_use = 1;
    g_pool.count++;
    
    return fd;
}

int remove_handle(int fd) {
    if (!g_pool.initialized || fd < 0) {
        return -1;
    }
    
    for (int i = 0; i < g_pool.capacity; i++) {
        if (g_pool.handles[i].in_use && g_pool.handles[i].fd == fd) {
            close(g_pool.handles[i].fd);
            
            if (g_pool.handles[i].filename) {
                free(g_pool.handles[i].filename);
                g_pool.handles[i].filename = NULL;
            }
            
            g_pool.handles[i].fd = INVALID_FD;
            g_pool.handles[i].flags = 0;
            g_pool.handles[i].in_use = 0;
            g_pool.count--;
            
            return 0;
        }
    }
    
    return -1;
}

int get_handle_by_filename(const char *filename) {
    if (!g_pool.initialized || !filename) {
        return INVALID_FD;
    }
    
    for (int i = 0; i < g_pool.capacity; i++) {
        if (g_pool.handles[i].in_use && 
            g_pool.handles[i].filename &&
            strcmp(g_pool.handles[i].filename, filename) == 0) {
            return g_pool.handles[i].fd;
        }
    }
    
    return INVALID_FD;
}

void cleanup(void) {
    if (!g_pool.initialized) {
        return;
    }
    
    for (int i = 0; i < g_pool.capacity; i++) {
        if (g_pool.handles[i].in_use) {
            if (g_pool.handles[i].fd >= 0) {
                close(g_pool.handles[i].fd);
            }
            
            if (g_pool.handles[i].filename) {
                free(g_pool.handles[i].filename);
                g_pool.handles[i].filename = NULL;
            }
            
            g_pool.handles[i].fd = INVALID_FD;
            g_pool.handles[i].flags = 0;
            g_pool.handles[i].in_use = 0;
        }
    }
    
    if (g_pool.handles) {
        free(g_pool.handles);
        g_pool.handles = NULL;
    }
    
    g_pool.capacity = 0;
    g_pool.count = 0;
    g_pool.initialized = 0;
}

int get_active_count(void) {
    if (!g_pool.initialized) {
        return 0;
    }
    return g_pool.count;
}

void print_pool_status(void) {
    if (!g_pool.initialized) {
        printf("Pool not initialized\n");
        return;
    }
    
    printf("Pool Status: %d/%d handles in use\n", g_pool.count, g_pool.capacity);
    
    if (g_pool.count > 0) {
        printf("Active handles:\n");
        for (int i = 0; i < g_pool.capacity; i++) {
            if (g_pool.handles[i].in_use) {
                printf("  [%d] fd=%d, file=%s, flags=0x%x\n",
                       i, g_pool.handles[i].fd,
                       g_pool.handles[i].filename ? g_pool.handles[i].filename : "(null)",
                       g_pool.handles[i].flags);
            }
        }
    }
}

int main(void) {
    printf("File Handle Manager Test\n");
    printf("=========================\n\n");
    
    if (init_pool(10) < 0) {
        fprintf(stderr, "Failed to initialize pool\n");
        return 1;
    }
    
    printf("Pool initialized with capacity: 10\n");
    print_pool_status();
    
    printf("\nAdding test files...\n");
    int fd1 = add_handle("/tmp/test1.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test1.txt: fd=%d\n", fd1);
    
    int fd2 = add_handle("/tmp/test2.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test2.txt: fd=%d\n", fd2);
    
    int fd3 = add_handle("/tmp/test3.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test3.txt: fd=%d\n", fd3);
    
    printf("\nCurrent pool status:\n");
    print_pool_status();
    
    printf("\nSearching for /tmp/test2.txt: fd=%d\n", 
           get_handle_by_filename("/tmp/test2.txt"));
    
    printf("\nRemoving fd=%d\n", fd2);
    if (remove_handle(fd2) == 0) {
        printf("Successfully removed\n");
    } else {
        printf("Failed to remove\n");
    }
    
    printf("\nPool after removal:\n");
    print_pool_status();
    
    printf("\nAdding another file...\n");
    int fd4 = add_handle("/tmp/test4.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test4.txt: fd=%d\n", fd4);
    
    print_pool_status();
    
    printf("\nCalling cleanup()...\n");
    cleanup();
    print_pool_status();
    
    printf("\nCalling cleanup() again (should be safe)...\n");
    cleanup();
    print_pool_status();
    
    printf("\nReinitializing after cleanup...\n");
    if (init_pool(5) < 0) {
        fprintf(stderr, "Failed to reinitialize pool\n");
        return 1;
    }
    
    int fd5 = add_handle("/tmp/test5.txt", O_CREAT | O_RDWR);
    printf("Added /tmp/test5.txt after reinit: fd=%d\n", fd5);
    
    print_pool_status();
    
    printf("\nFinal cleanup...\n");
    cleanup();
    
    unlink("/tmp/test1.txt");
    unlink("/tmp/test2.txt");
    unlink("/tmp/test3.txt");
    unlink("/tmp/test4.txt");
    unlink("/tmp/test5.txt");
    
    printf("\nTest completed successfully!\n");
    
    return 0;
}