SessionEntry *create_session(SessionCache *cache,
                             const char *session_id,
                             const char *user_id,
                             const char *data,
                             unsigned int ttl_seconds) {
    SessionEntry *entry;
    unsigned long index;
    char *new_user_id;
    char *new_data;