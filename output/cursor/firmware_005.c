#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <stdlib.h>
#include <ctype.h>

#define CMD_BUF_SZ 48

static char g_cmd[CMD_BUF_SZ];
static unsigned g_len;

/* Example sensor settings — map to your hardware */
static uint16_t g_sample_ms = 1000;
static uint8_t g_tx_power = 7;
static uint8_t g_sensor_en = 1;

static int uart_rx_byte(void) {
    return getchar();
}

static void trim(char *s) {
    char *e;
    for (e = s + strlen(s); e > s && isspace((unsigned char)e[-1]); --e)
        *e = '\0';
}

static void apply_kv(char *key, char *val) {
    unsigned long u;
    if (!strcmp(key, "SAMPLE_MS")) {
        u = strtoul(val, NULL, 10);
        if (u > 0 && u <= 60000)
            g_sample_ms = (uint16_t)u;
    } else if (!strcmp(key, "TXPWR")) {
        u = strtoul(val, NULL, 10);
        if (u <= 15)
            g_tx_power = (uint8_t)u;
    } else if (!strcmp(key, "SEN")) {
        u = strtoul(val, NULL, 10);
        g_sensor_en = (u != 0);
    }
}

static void handle_line(char *line) {
    char *eq;

    while (*line && isspace((unsigned char)*line))
        line++;
    if (*line == '\0' || *line == '#')
        return;

    eq = strchr(line, '=');
    if (!eq)
        return;
    *eq = '\0';
    trim(line);
    eq++;
    while (*eq && isspace((unsigned char)*eq))
        eq++;
    trim(eq);
    if (*line && *eq)
        apply_kv(line, eq);
}

static void feed_byte(int c) {
    if (c == '\r')
        return;
    if (c == '\n') {
        if (g_len < CMD_BUF_SZ)
            g_cmd[g_len] = '\0';
        else
            g_cmd[CMD_BUF_SZ - 1] = '\0';
        if (g_len)
            handle_line(g_cmd);
        g_len = 0;
        return;
    }
    if (g_len + 1 < CMD_BUF_SZ)
        g_cmd[g_len++] = (char)c;
    else
        g_len = 0;
}

void serial_config_task(void) {
    int c;

    for (;;) {
        c = uart_rx_byte();
        if (c < 0)
            continue;
        feed_byte(c);
    }
}

int main(void) {
    serial_config_task();
    return 0;
}