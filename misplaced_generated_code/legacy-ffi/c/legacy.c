#include <stdlib.h>
#include <string.h>

typedef struct LegacyBuffer {
    unsigned char *data;
    size_t len;
    size_t cap;
} LegacyBuffer;

LegacyBuffer *legacy_buffer_new(size_t initial_cap) {
    LegacyBuffer *b = (LegacyBuffer *)calloc(1, sizeof(LegacyBuffer));
    if (!b) return NULL;
    if (initial_cap > 0) {
        b->data = (unsigned char *)malloc(initial_cap);
        if (!b->data) {
            free(b);
            return NULL;
        }
        b->cap = initial_cap;
    }
    return b;
}

void legacy_buffer_free(LegacyBuffer *b) {
    if (!b) return;
    free(b->data);
    free(b);
}

int legacy_buffer_push(LegacyBuffer *b, const unsigned char *src, size_t n) {
    if (!b || (!src && n > 0)) return -1;
    size_t need = b->len + n;
    if (need > b->cap) {
        size_t new_cap = b->cap ? b->cap : 8;
        while (new_cap < need) new_cap *= 2;
        unsigned char *p = (unsigned char *)realloc(b->data, new_cap);
        if (!p) return -1;
        b->data = p;
        b->cap = new_cap;
    }
    if (n > 0) memcpy(b->data + b->len, src, n);
    b->len = need;
    return 0;
}

size_t legacy_buffer_len(const LegacyBuffer *b) {
    return b ? b->len : 0;
}

const unsigned char *legacy_buffer_data(const LegacyBuffer *b) {
    return b ? b->data : NULL;
}
