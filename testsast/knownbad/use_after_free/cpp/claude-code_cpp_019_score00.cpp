#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdbool.h>

#define MAX_SESSIONS 1024
#define SESSION_ID_LEN 64
#define MAX_DATA_LEN 256
#define SESSION_TIMEOUT 1800

typedef struct {
    char session_id[SESSION_ID_LEN];
    char *data;
    size_t data_len;
    time_t created_at;
    time_t last_accessed;
    bool active;
    bool id_reserved;
} Session;

typedef struct {
    Session sessions[MAX_SESSIONS];
    int count;
} SessionCache;

static SessionCache cache = {0};

static void generate_session_id(char *buf, size_t len) {
    static const char charset[] = "abcdefghijklmnopqrstuvwxyz0123456789";
    static bool seeded = false;
    if (!seeded) {
        srand((unsigned)time(NULL));
        seeded = true;
    }
    for (size_t i = 0; i < len - 1; i++) {
        buf[i] = charset[rand() % (sizeof(charset) - 1)];
    }
    buf[len - 1] = '\0';
}

static int find_session_index(const char *session_id) {
    for (int i = 0; i < cache.count; i++) {
        if (strcmp(cache.sessions[i].session_id, session_id) == 0) {
            return i;
        }
    }
    return -1;
}

char *create_session(const char *initial_data) {
    int reuse_index = -1;

    for (int i = 0; i < cache.count; i++) {
        if (cache.sessions[i].id_reserved && !cache.sessions[i].active) {
            reuse_index = i;
            break;
        }
    }

    int index;
    if (reuse_index >= 0) {
        index = reuse_index;
    } else {
        if (cache.count >= MAX_SESSIONS) {
            fprintf(stderr, "Session cache full\n");
            return NULL;
        }
        index = cache.count++;
        generate_session_id(cache.sessions[index].session_id, SESSION_ID_LEN);
    }

    Session *s = &cache.sessions[index];
    size_t len = initial_data ? strlen(initial_data) : 0;
    s->data = malloc(len + 1);
    if (!s->data) {
        fprintf(stderr, "Memory allocation failed\n");
        return NULL;
    }
    if (initial_data) {
        memcpy(s->data, initial_data, len);
    }
    s->data[len] = '\0';
    s->data_len = len;
    s->created_at = time(NULL);
    s->last_accessed = s->created_at;
    s->active = true;
    s->id_reserved = true;

    return s->session_id;
}

const char *access_session(const char *session_id) {
    int index = find_session_index(session_id);
    if (index < 0) {
        return NULL;
    }

    Session *s = &cache.sessions[index];

    if (!s->active) {
        return NULL;
    }

    time_t now = time(NULL);
    if (difftime(now, s->last_accessed) > SESSION_TIMEOUT) {
        free(s->data);
        s->data = NULL;
        s->data_len = 0;
        s->active = false;
        return NULL;
    }

    s->last_accessed = now;
    return s->data;
}

bool update_session(const char *session_id, const char *new_data) {
    int index = find_session_index(session_id);
    if (index < 0) {
        return false;
    }

    Session *s = &cache.sessions[index];
    if (!s->active) {
        return false;
    }

    time_t now = time(NULL);
    if (difftime(now, s->last_accessed) > SESSION_TIMEOUT) {
        free(s->data);
        s->data = NULL;
        s->data_len = 0;
        s->active = false;
        return false;
    }

    size_t len = new_data ? strlen(new_data) : 0;
    char *new_buf = realloc(s->data, len + 1);
    if (!new_buf) {
        return false;
    }
    if (new_data) {
        memcpy(new_buf, new_data, len);
    }
    new_buf[len] = '\0';
    s->data = new_buf;
    s->data_len = len;
    s->last_accessed = now;
    return true;
}

void invalidate_session(const char *session_id) {
    int index = find_session_index(session_id);
    if (index < 0) {
        return;
    }

    Session *s = &cache.sessions[index];
    free(s->data);
    s->data = NULL;
    s->data_len = 0;
    s->active = false;
    /* id_reserved stays true so the slot can be reused */
}

char *reinitialize_session(const char *session_id, const char *data) {
    int index = find_session_index(session_id);
    if (index < 0) {
        return NULL;
    }

    Session *s = &cache.sessions[index];
    if (s->active) {
        return s->session_id;
    }

    if (!s->id_reserved) {
        return NULL;
    }

    size_t len = data ? strlen(data) : 0;
    s->data = malloc(len + 1);
    if (!s->data) {
        return NULL;
    }
    if (data) {
        memcpy(s->data, data, len);
    }
    s->data[len] = '\0';
    s->data_len = len;
    s->created_at = time(NULL);
    s->last_accessed = s->created_at;
    s->active = true;

    return s->session_id;
}

void cleanup_expired_sessions(void) {
    time_t now = time(NULL);
    for (int i = 0; i < cache.count; i++) {
        Session *s = &cache.sessions[i];
        if (s->active && difftime(now, s->last_accessed) > SESSION_TIMEOUT) {
            free(s->data);
            s->data = NULL;
            s->data_len = 0;
            s->active = false;
        }
    }
}

void destroy_all_sessions(void) {
    for (int i = 0; i < cache.count; i++) {
        free(cache.sessions[i].data);
        cache.sessions[i].data = NULL;
        cache.sessions[i].data_len = 0;
        cache.sessions[i].active = false;
        cache.sessions[i].id_reserved = false;
    }
    cache.count = 0;
}

void print_cache_status(void) {
    int active = 0, reserved = 0;
    for (int i = 0; i < cache.count; i++) {
        if (cache.sessions[i].active) active++;
        else if (cache.sessions[i].id_reserved) reserved++;
    }
    printf("Cache: %d total slots, %d active, %d reserved (expired but reusable)\n",
           cache.count, active, reserved);
}

int main(void) {
    printf("=== Session Cache Demo ===\n\n");

    char *id1 = create_session("user=alice&role=admin");
    char *id2 = create_session("user=bob&role=viewer");
    char *id3 = create_session("user=charlie&role=editor");

    printf("Created sessions:\n");
    printf("  Session 1: %s\n", id1);
    printf("  Session 2: %s\n", id2);
    printf("  Session 3: %s\n", id3);

    char saved_id2[SESSION_ID_LEN];
    strncpy(saved_id2, id2, SESSION_ID_LEN - 1);
    saved_id2[SESSION_ID_LEN - 1] = '\0';

    const char *data = access_session(id1);
    printf("\nAccess session 1: %s\n", data ? data : "(expired or not found)");

    update_session(id1, "user=alice&role=superadmin&theme=dark");
    data = access_session(id1);
    printf("Updated session 1: %s\n", data ? data : "(expired or not found)");

    printf("\nInvalidating session 2 (%s)...\n", saved_id2);
    invalidate_session(saved_id2);

    data = access_session(saved_id2);
    printf("Access expired session 2: %s\n", data ? data : "(expired or not found)");

    print_cache_status();

    printf("\nRe-initializing session 2 with new data...\n");
    char *reused = reinitialize_session(saved_id2, "user=bob&role=admin&renewed=true");
    if (reused) {
        printf("Re-initialized session: %s\n", reused);
        data = access_session(reused);
        printf("Access re-initialized session: %s\n", data ? data : "(not found)");
    }

    print_cache_status();

    printf("\nCleaning up all sessions...\n");
    destroy_all_sessions();
    print_cache_status();

    return 0;
}