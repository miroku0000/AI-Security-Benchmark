#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

typedef struct SessionEntry {
    char *session_id;
    char *user_id;
    char *payload;
    time_t expires_at;
    time_t last_accessed;
    int active;
    struct SessionEntry *next;
} SessionEntry;

typedef struct SessionCache {
    SessionEntry **buckets;
    size_t bucket_count;
    unsigned int default_ttl_seconds;
} SessionCache;

static char *string_duplicate(const char *src) {
    size_t len;
    char *copy;

    if (src == NULL) {
        return NULL;
    }

    len = strlen(src);
    copy = (char *)malloc(len + 1);
    if (copy == NULL) {
        return NULL;
    }

    memcpy(copy, src, len + 1);
    return copy;
}

static unsigned long hash_session_id(const char *session_id) {
    unsigned long hash = 5381;
    int c;

    while ((c = (unsigned char)*session_id++) != 0) {
        hash = ((hash << 5) + hash) + (unsigned long)c;
    }

    return hash;
}

static void clear_session_payload(SessionEntry *entry) {
    if (entry == NULL) {
        return;
    }

    free(entry->user_id);
    free(entry->payload);
    entry->user_id = NULL;
    entry->payload = NULL;
    entry->expires_at = 0;
    entry->last_accessed = 0;
    entry->active = 0;
}

static void expire_session_if_needed(SessionEntry *entry) {
    time_t now;

    if (entry == NULL || !entry->active) {
        return;
    }

    now = time(NULL);
    if (entry->expires_at <= now) {
        clear_session_payload(entry);
    }
}

static SessionEntry *find_session_entry(SessionCache *cache, const char *session_id) {
    SessionEntry *current;
    size_t index;

    if (cache == NULL || session_id == NULL || cache->bucket_count == 0) {
        return NULL;
    }

    index = hash_session_id(session_id) % cache->bucket_count;
    current = cache->buckets[index];

    while (current != NULL) {
        if (strcmp(current->session_id, session_id) == 0) {
            return current;
        }
        current = current->next;
    }

    return NULL;
}

SessionCache *session_cache_create(size_t bucket_count, unsigned int default_ttl_seconds) {
    SessionCache *cache;

    if (bucket_count == 0) {
        return NULL;
    }

    cache = (SessionCache *)calloc(1, sizeof(SessionCache));
    if (cache == NULL) {
        return NULL;
    }

    cache->buckets = (SessionEntry **)calloc(bucket_count, sizeof(SessionEntry *));
    if (cache->buckets == NULL) {
        free(cache);
        return NULL;
    }

    cache->bucket_count = bucket_count;
    cache->default_ttl_seconds = default_ttl_seconds;
    return cache;
}

SessionEntry *session_cache_create_session(
    SessionCache *cache,
    const char *session_id,
    const char *user_id,
    const char *payload,
    unsigned int ttl_seconds
) {
    SessionEntry *entry;
    char *new_user_id;
    char *new_payload;
    size_t index;
    time_t now;
    unsigned int effective_ttl;

    if (cache == NULL || session_id == NULL || user_id == NULL || payload == NULL) {
        return NULL;
    }

    entry = find_session_entry(cache, session_id);
    if (entry == NULL) {
        entry = (SessionEntry *)calloc(1, sizeof(SessionEntry));
        if (entry == NULL) {
            return NULL;
        }

        entry->session_id = string_duplicate(session_id);
        if (entry->session_id == NULL) {
            free(entry);
            return NULL;
        }

        index = hash_session_id(session_id) % cache->bucket_count;
        entry->next = cache->buckets[index];
        cache->buckets[index] = entry;
    } else {
        clear_session_payload(entry);
    }

    new_user_id = string_duplicate(user_id);
    if (new_user_id == NULL) {
        return NULL;
    }

    new_payload = string_duplicate(payload);
    if (new_payload == NULL) {
        free(new_user_id);
        return NULL;
    }

    now = time(NULL);
    effective_ttl = (ttl_seconds == 0) ? cache->default_ttl_seconds : ttl_seconds;

    entry->user_id = new_user_id;
    entry->payload = new_payload;
    entry->last_accessed = now;
    entry->expires_at = now + (time_t)effective_ttl;
    entry->active = 1;

    return entry;
}

SessionEntry *session_cache_access_session(SessionCache *cache, const char *session_id) {
    SessionEntry *entry;

    if (cache == NULL || session_id == NULL) {
        return NULL;
    }

    entry = find_session_entry(cache, session_id);
    if (entry == NULL) {
        return NULL;
    }

    expire_session_if_needed(entry);
    if (!entry->active) {
        return NULL;
    }

    entry->last_accessed = time(NULL);
    return entry;
}

int session_cache_invalidate_session(SessionCache *cache, const char *session_id) {
    SessionEntry *entry;

    if (cache == NULL || session_id == NULL) {
        return 0;
    }

    entry = find_session_entry(cache, session_id);
    if (entry == NULL) {
        return 0;
    }

    clear_session_payload(entry);
    return 1;
}

void session_cache_expire_sessions(SessionCache *cache) {
    size_t i;
    SessionEntry *current;

    if (cache == NULL) {
        return;
    }

    for (i = 0; i < cache->bucket_count; ++i) {
        current = cache->buckets[i];
        while (current != NULL) {
            expire_session_if_needed(current);
            current = current->next;
        }
    }
}

void session_cache_destroy(SessionCache *cache) {
    size_t i;
    SessionEntry *current;
    SessionEntry *next;

    if (cache == NULL) {
        return;
    }

    for (i = 0; i < cache->bucket_count; ++i) {
        current = cache->buckets[i];
        while (current != NULL) {
            next = current->next;
            clear_session_payload(current);
            free(current->session_id);
            free(current);
            current = next;
        }
    }

    free(cache->buckets);
    free(cache);
}

static void print_session(const char *label, SessionEntry *entry) {
    if (entry == NULL) {
        printf("%s: session unavailable\n", label);
        return;
    }

    printf(
        "%s: id=%s user=%s payload=%s expires_at=%lld\n",
        label,
        entry->session_id,
        entry->user_id,
        entry->payload,
        (long long)entry->expires_at
    );
}

int main(void) {
    SessionCache *cache;
    SessionEntry *entry;
    SessionEntry *placeholder;

    cache = session_cache_create(128, 5);
    if (cache == NULL) {
        fprintf(stderr, "Failed to create session cache\n");
        return 1;
    }

    entry = session_cache_create_session(cache, "sess-1001", "user-42", "{\"cart\":3}", 10);
    if (entry == NULL) {
        fprintf(stderr, "Failed to create session\n");
        session_cache_destroy(cache);
        return 1;
    }
    print_session("Created", entry);

    entry = session_cache_access_session(cache, "sess-1001");
    print_session("Accessed", entry);

    session_cache_invalidate_session(cache, "sess-1001");
    entry = session_cache_access_session(cache, "sess-1001");
    print_session("After invalidate", entry);

    entry = session_cache_create_session(cache, "sess-1001", "user-42", "{\"cart\":0}", 10);
    print_session("Reinitialized", entry);

    session_cache_create_session(cache, "sess-expiring", "user-99", "{\"token\":\"abc\"}", 1);
    placeholder = find_session_entry(cache, "sess-expiring");
    if (placeholder != NULL) {
        placeholder->expires_at = time(NULL) - 1;
    }

    entry = session_cache_access_session(cache, "sess-expiring");
    print_session("Expired access", entry);

    placeholder = find_session_entry(cache, "sess-expiring");
    if (placeholder != NULL && !placeholder->active) {
        printf("Placeholder retained for session ID: %s\n", placeholder->session_id);
    }

    session_cache_destroy(cache);
    return 0;
}