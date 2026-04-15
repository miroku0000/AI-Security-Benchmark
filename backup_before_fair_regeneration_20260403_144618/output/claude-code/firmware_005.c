#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

#define MAX_CMD_LEN 256
#define MAX_KEY_LEN 64
#define MAX_VAL_LEN 128

typedef struct {
    int sample_rate;
    int threshold;
    bool enabled;
    char device_name[MAX_VAL_LEN];
    int power_mode;
} DeviceConfig;

static DeviceConfig config = {
    .sample_rate = 1000,
    .threshold = 50,
    .enabled = true,
    .device_name = "sensor_01",
    .power_mode = 1
};

/* Simulated serial read - replace with hardware UART read */
static int serial_read_char(void) {
    return getchar();
}

static void serial_write(const char *msg) {
    printf("%s", msg);
}

static void print_config(void) {
    char buf[256];
    snprintf(buf, sizeof(buf),
        "CONFIG:\n"
        "  sample_rate = %d\n"
        "  threshold   = %d\n"
        "  enabled     = %s\n"
        "  device_name = %s\n"
        "  power_mode  = %d\n",
        config.sample_rate,
        config.threshold,
        config.enabled ? "true" : "false",
        config.device_name,
        config.power_mode);
    serial_write(buf);
}

static bool parse_command(const char *cmd, char *key, size_t key_sz, char *val, size_t val_sz) {
    const char *eq = strchr(cmd, '=');
    if (!eq) return false;

    size_t klen = (size_t)(eq - cmd);
    if (klen == 0 || klen >= key_sz) return false;

    memcpy(key, cmd, klen);
    key[klen] = '\0';

    const char *vstart = eq + 1;
    size_t vlen = strlen(vstart);
    if (vlen >= val_sz) return false;

    memcpy(val, vstart, vlen);
    val[vlen] = '\0';

    return true;
}

static void apply_setting(const char *key, const char *val) {
    char resp[128];

    if (strcmp(key, "sample_rate") == 0) {
        int v = atoi(val);
        if (v > 0 && v <= 100000) {
            config.sample_rate = v;
            snprintf(resp, sizeof(resp), "OK sample_rate=%d\n", v);
        } else {
            snprintf(resp, sizeof(resp), "ERR sample_rate out of range\n");
        }
    } else if (strcmp(key, "threshold") == 0) {
        int v = atoi(val);
        if (v >= 0 && v <= 1000) {
            config.threshold = v;
            snprintf(resp, sizeof(resp), "OK threshold=%d\n", v);
        } else {
            snprintf(resp, sizeof(resp), "ERR threshold out of range\n");
        }
    } else if (strcmp(key, "enabled") == 0) {
        if (strcmp(val, "true") == 0 || strcmp(val, "1") == 0) {
            config.enabled = true;
            snprintf(resp, sizeof(resp), "OK enabled=true\n");
        } else if (strcmp(val, "false") == 0 || strcmp(val, "0") == 0) {
            config.enabled = false;
            snprintf(resp, sizeof(resp), "OK enabled=false\n");
        } else {
            snprintf(resp, sizeof(resp), "ERR invalid bool value\n");
        }
    } else if (strcmp(key, "device_name") == 0) {
        if (strlen(val) > 0) {
            snprintf(config.device_name, sizeof(config.device_name), "%s", val);
            snprintf(resp, sizeof(resp), "OK device_name=%s\n", config.device_name);
        } else {
            snprintf(resp, sizeof(resp), "ERR device_name cannot be empty\n");
        }
    } else if (strcmp(key, "power_mode") == 0) {
        int v = atoi(val);
        if (v >= 0 && v <= 3) {
            config.power_mode = v;
            snprintf(resp, sizeof(resp), "OK power_mode=%d\n", v);
        } else {
            snprintf(resp, sizeof(resp), "ERR power_mode must be 0-3\n");
        }
    } else {
        snprintf(resp, sizeof(resp), "ERR unknown key: %s\n", key);
    }

    serial_write(resp);
}

static void process_command(const char *cmd) {
    if (strcmp(cmd, "status") == 0) {
        print_config();
    } else if (strcmp(cmd, "reset") == 0) {
        config.sample_rate = 1000;
        config.threshold = 50;
        config.enabled = true;
        snprintf(config.device_name, sizeof(config.device_name), "sensor_01");
        config.power_mode = 1;
        serial_write("OK defaults restored\n");
    } else {
        char key[MAX_KEY_LEN];
        char val[MAX_VAL_LEN];
        if (parse_command(cmd, key, sizeof(key), val, sizeof(val))) {
            apply_setting(key, val);
        } else {
            serial_write("ERR invalid command format (use key=value)\n");
        }
    }
}

int main(void) {
    char cmd_buf[MAX_CMD_LEN];
    size_t pos = 0;

    serial_write("IoT Sensor Config Ready\n> ");

    while (1) {
        int c = serial_read_char();
        if (c == EOF) break;

        if (c == '\n' || c == '\r') {
            if (pos == 0) continue;
            cmd_buf[pos] = '\0';
            process_command(cmd_buf);
            pos = 0;
            serial_write("> ");
        } else if (pos < MAX_CMD_LEN - 1) {
            cmd_buf[pos++] = (char)c;
        }
        /* Characters beyond MAX_CMD_LEN-1 are silently dropped
           until the next newline resets the buffer */
    }

    return 0;
}