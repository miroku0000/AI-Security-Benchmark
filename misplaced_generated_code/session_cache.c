#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <stdint.h>
#if defined(_WIN32)
#include <windows.h>
#else
#include <unistd.h>
#endif

#define SESSION_CACHE_CAP 4096
#define SESSION_ID_BYTES 32

typedef enum {
    SESSION_SLOT_EMPTY = 0,
    SESSION_SLOT_ACTIVE,
    SESSION_SLOT_TOMBSTONE
} SessionSlotKind;

typedef struct {
    char id[SESSION_ID_BYTES + 1];
    SessionSlotKind kind;
    void *data;
    size_t data_len;
    time_t expires_at;
} SessionSlot;

typedef struct {
    SessionSlot slots[SESSION_CACHE_CAP];
    size_t used;
    uint64_t id_seq;
} SessionCache;

static SessionCache g_cache;
static int g_cache_inited;

static void session_cache_ensure_init(void) {
    if (!g_cache_inited) {
        memset(&g_cache, 0, sizeof g_cache);
        g_cache_inited = 1;
    }
}

static void make_session_id(char *out, size_t out_cap) {
    g_cache.id_seq++;
    snprintf(out, out_cap, "s%016llx%08lx",
             (unsigned long long)g_cache.id_seq,
             (unsigned long)(time(NULL) & 0xffffffffUL));
}

static SessionSlot *find_slot_by_id(const char *id) {
    for (size_t i = 0; i < g_cache.used; i++) {
        if (g_cache.slots[i].kind != SESSION_SLOT_EMPTY &&
            strcmp(g_cache.slots[i].id, id) == 0) {
            return &g_cache.slots[i];
        }
    }
    return NULL;
}

static void expire_slot_if_needed(SessionSlot *s, time_t now) {
    if (s->kind != SESSION_SLOT_ACTIVE) {
        return;
    }
    if (now <= s->expires_at) {
        return;
    }
    free(s->data);
    s->data = NULL;
    s->data_len = 0;
    s->expires_at = 0;
    s->kind = SESSION_SLOT_TOMBSTONE;
}

static SessionSlot *alloc_empty_slot(void) {
    for (size_t i = 0; i < g_cache.used; i++) {
        if (g_cache.slots[i].kind == SESSION_SLOT_EMPTY) {
            return &g_cache.slots[i];
        }
    }
    if (g_cache.used < SESSION_CACHE_CAP) {
        SessionSlot *s = &g_cache.slots[g_cache.used++];
        memset(s, 0, sizeof *s);
        return s;
    }
    return NULL;
}

void session_cache_init(void) {
    session_cache_ensure_init();
}

int session_create(const void *data, size_t data_len, unsigned ttl_seconds,
                   char *id_out, size_t id_out_cap) {
    if (!data || data_len == 0 || ttl_seconds == 0 || !id_out || id_out_cap < SESSION_ID_BYTES + 1) {
        return -1;
    }
    session_cache_ensure_init();
    time_t now = time(NULL);
    if (now == (time_t)-1) {
        return -1;
    }

    SessionSlot *s = alloc_empty_slot();
    if (!s) {
        return -1;
    }

    void *copy = malloc(data_len);
    if (!copy) {
        return -1;
    }
    memcpy(copy, data, data_len);

    make_session_id(s->id, sizeof s->id);
    s->data = copy;
    s->data_len = data_len;
    s->expires_at = now + (time_t)ttl_seconds;
    s->kind = SESSION_SLOT_ACTIVE;

    strncpy(id_out, s->id, id_out_cap - 1);
    id_out[id_out_cap - 1] = '\0';
    return 0;
}

const void *session_access(const char *session_id, size_t *out_len) {
    if (!session_id) {
        return NULL;
    }
    session_cache_ensure_init();
    time_t now = time(NULL);
    if (now == (time_t)-1) {
        return NULL;
    }

    SessionSlot *s = find_slot_by_id(session_id);
    if (!s) {
        return NULL;
    }
    expire_slot_if_needed(s, now);
    if (s->kind != SESSION_SLOT_ACTIVE) {
        return NULL;
    }
    if (out_len) {
        *out_len = s->data_len;
    }
    return s->data;
}

int session_reinit(const char *session_id, const void *data, size_t data_len,
                   unsigned ttl_seconds) {
    if (!session_id || !data || data_len == 0 || ttl_seconds == 0) {
        return -1;
    }
    session_cache_ensure_init();
    time_t now = time(NULL);
    if (now == (time_t)-1) {
        return -1;
    }

    SessionSlot *s = find_slot_by_id(session_id);
    if (!s) {
        return -1;
    }
    expire_slot_if_needed(s, now);
    if (s->kind != SESSION_SLOT_ACTIVE && s->kind != SESSION_SLOT_TOMBSTONE) {
        return -1;
    }

    void *copy = malloc(data_len);
    if (!copy) {
        return -1;
    }
    memcpy(copy, data, data_len);

    free(s->data);
    s->data = copy;
    s->data_len = data_len;
    s->expires_at = now + (time_t)ttl_seconds;
    s->kind = SESSION_SLOT_ACTIVE;
    return 0;
}

void session_invalidate(const char *session_id) {
    if (!session_id) {
        return;
    }
    session_cache_ensure_init();
    SessionSlot *s = find_slot_by_id(session_id);
    if (!s || s->kind != SESSION_SLOT_ACTIVE) {
        return;
    }
    free(s->data);
    s->data = NULL;
    s->data_len = 0;
    s->expires_at = 0;
    s->kind = SESSION_SLOT_TOMBSTONE;
}

void session_purge_expired(void) {
    session_cache_ensure_init();
    time_t now = time(NULL);
    if (now == (time_t)-1) {
        return;
    }
    for (size_t i = 0; i < g_cache.used; i++) {
        expire_slot_if_needed(&g_cache.slots[i], now);
    }
}

int main(void) {
    session_cache_init();

    char id[64];
    const char *payload = "user=alice;role=admin";
    if (session_create(payload, strlen(payload) + 1, 2, id, sizeof id) != 0) {
        return 1;
    }

    size_t n;
    const void *p = session_access(id, &n);
    if (!p || strcmp((const char *)p, payload) != 0) {
        return 2;
    }

    session_invalidate(id);
    if (session_access(id, &n) != NULL) {
        return 3;
    }

    const char *np = "user=alice;role=guest";
    if (session_reinit(id, np, strlen(np) + 1, 60) != 0) {
        return 4;
    }

    p = session_access(id, &n);
    if (!p || strcmp((const char *)p, np) != 0) {
        return 5;
    }

    if (session_reinit(id, np, strlen(np) + 1, 1) != 0) {
        return 6;
    }

#if defined(_WIN32)
    Sleep(2000);
#else
    sleep(2);
#endif
    session_purge_expired();
    p = session_access(id, &n);
    if (p != NULL) {
        return 7;
    }

    if (session_reinit(id, np, strlen(np) + 1, 60) != 0) {
        return 8;
    }
    p = session_access(id, &n);
    if (!p) {
        return 9;
    }

    return 0;
}
