#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#define CMD_BUF_SIZE 64

typedef struct {
    int sample_rate_hz;
    int threshold;
    int enabled;
} device_config_t;

static device_config_t g_cfg = {10, 100, 1};

static void serial_write(const char *s) {
    fputs(s, stdout);
    fflush(stdout);
}

static int serial_read_line(char *buf, size_t size) {
    size_t i = 0;
    int c;

    if (size == 0) {
        return 0;
    }

    while ((c = getchar()) != EOF) {
        if (c == '\r') {
            continue;
        }
        if (c == '\n') {
            break;
        }
        if (i + 1 < size) {
            buf[i++] = (char)c;
        }
    }

    if (c == EOF && i == 0) {
        return 0;
    }

    buf[i] = '\0';
    return 1;
}

static int parse_set_command(const char *buf, char *key, size_t key_size, long *value) {
    char extra;
    return sscanf(buf, "SET %15s %ld %c", key, value, &extra) == 2;
}

static void print_config(void) {
    char out[96];
    snprintf(out, sizeof(out),
             "RATE=%d THRESHOLD=%d ENABLE=%d\n",
             g_cfg.sample_rate_hz, g_cfg.threshold, g_cfg.enabled);
    serial_write(out);
}

static void apply_command(const char *buf) {
    char key[16];
    long value;

    if (strcmp(buf, "GET") == 0) {
        print_config();
        return;
    }

    if (strcmp(buf, "HELP") == 0) {
        serial_write("SET RATE <1-1000>\nSET THRESHOLD <0-4095>\nSET ENABLE <0|1>\nGET\n");
        return;
    }

    if (!parse_set_command(buf, key, sizeof(key), &value)) {
        serial_write("ERR\n");
        return;
    }

    if (strcmp(key, "RATE") == 0) {
        if (value < 1 || value > 1000) {
            serial_write("ERR\n");
            return;
        }
        g_cfg.sample_rate_hz = (int)value;
        serial_write("OK\n");
        return;
    }

    if (strcmp(key, "THRESHOLD") == 0) {
        if (value < 0 || value > 4095) {
            serial_write("ERR\n");
            return;
        }
        g_cfg.threshold = (int)value;
        serial_write("OK\n");
        return;
    }

    if (strcmp(key, "ENABLE") == 0) {
        if (value != 0 && value != 1) {
            serial_write("ERR\n");
            return;
        }
        g_cfg.enabled = (int)value;
        serial_write("OK\n");
        return;
    }

    serial_write("ERR\n");
}

int main(void) {
    char cmd[CMD_BUF_SIZE];

    serial_write("READY\n");

    while (serial_read_line(cmd, sizeof(cmd))) {
        if (cmd[0] == '\0') {
            continue;
        }
        apply_command(cmd);
    }

    return 0;
}