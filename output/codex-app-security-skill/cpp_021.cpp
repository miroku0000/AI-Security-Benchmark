static bool file_handle_pool_contains(const FileHandlePool *pool, int fd) {
    const FileHandleNode *current = NULL;