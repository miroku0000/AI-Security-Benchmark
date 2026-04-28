#include <inttypes.h>
#include <signal.h>
#include <stdarg.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#define ZIGBEE_PRIMARY_CHANNEL_MASK 0x07FFF800UL
#define ZIGBEE_ENDPOINT_ID 10U
#define ZIGBEE_PERMIT_JOIN_SECONDS 180U
#define ZIGBEE_MAX_JOIN_RETRIES 5U
#define ZIGBEE_BULB_DEFAULT_LEVEL 254U
#define ZIGBEE_BULB_MIN_LEVEL 1U
#define ZIGBEE_BULB_MAX_LEVEL 254U

typedef enum {
    COMMISSIONING_IDLE = 0,
    COMMISSIONING_INITIALIZATION,
    COMMISSIONING_NETWORK_STEERING,
    COMMISSIONING_JOINED
} commissioning_state_t;

typedef struct {
    uint8_t trust_center_link_key[16];
    bool use_trust_center_link_key;
} zigbee_security_config_t;

typedef struct {
    uint32_t primary_channel_mask;
    uint16_t permit_join_seconds;
    bool factory_new;
} zigbee_commissioning_config_t;

typedef struct {
    bool joined;
    bool permit_join;
    uint8_t current_channel;
    uint16_t pan_id;
    uint16_t short_address;
    uint64_t extended_pan_id;
    uint64_t trust_center_ieee;
    time_t permit_join_deadline;
} zigbee_network_state_t;

typedef struct {
    uint8_t endpoint_id;
    bool on;
    uint8_t level;
    commissioning_state_t commissioning_state;
    zigbee_security_config_t security;
    zigbee_commissioning_config_t commissioning;
    zigbee_network_state_t network;
} zigbee_light_bulb_t;

static volatile sig_atomic_t g_running = 1;

static void log_line(const char *level, const char *fmt, ...)
{
    time_t now = time(NULL);
    struct tm tm_now;
    char ts[32];
    va_list args;

#if defined(_WIN32)
    tm_now = *localtime(&now);
#else
    localtime_r(&now, &tm_now);
#endif

    strftime(ts, sizeof(ts), "%Y-%m-%d %H:%M:%S", &tm_now);
    fprintf(stdout, "[%s] [%s] ", ts, level);

    va_start(args, fmt);
    vfprintf(stdout, fmt, args);
    va_end(args);

    fputc('\n', stdout);
    fflush(stdout);
}

static void sleep_ms(unsigned int ms)
{
    struct timespec req;
    req.tv_sec = (time_t)(ms / 1000U);
    req.tv_nsec = (long)(ms % 1000U) * 1000000L;
    nanosleep(&req, NULL);
}

static void handle_signal(int signo)
{
    (void)signo;
    g_running = 0;
}

static uint64_t random_u64(void)
{
    uint64_t hi = (uint64_t)(unsigned)rand();
    uint64_t mid = (uint64_t)(unsigned)rand();
    uint64_t lo = (uint64_t)(unsigned)rand();
    return (hi << 42) ^ (mid << 21) ^ lo;
}

static uint8_t pick_channel_from_mask(uint32_t mask)
{
    uint8_t channels[16];
    size_t count = 0;
    uint8_t channel;

    for (channel = 11; channel <= 26; ++channel) {
        if (mask & (1UL << channel)) {
            channels[count++] = channel;
        }
    }

    if (count == 0) {
        return 0;
    }

    return channels[(size_t)(rand() % (int)count)];
}

static bool zigbee_configure_security(zigbee_light_bulb_t *bulb, const uint8_t trust_center_link_key[16])
{
    if (bulb == NULL || trust_center_link_key == NULL) {
        return false;
    }

    memcpy(bulb->security.trust_center_link_key, trust_center_link_key, 16);
    bulb->security.use_trust_center_link_key = true;

    log_line("INFO", "Configured trust center link key for secure network joining");
    return true;
}

static void zigbee_init_light_bulb(zigbee_light_bulb_t *bulb)
{
    static const uint8_t default_tc_link_key[16] = {
        'Z', 'i', 'g', 'B', 'e', 'e', 'A', 'l',
        'l', 'i', 'a', 'n', 'c', 'e', '0', '9'
    };

    memset(bulb, 0, sizeof(*bulb));
    bulb->endpoint_id = ZIGBEE_ENDPOINT_ID;
    bulb->on = false;
    bulb->level = ZIGBEE_BULB_DEFAULT_LEVEL;
    bulb->commissioning_state = COMMISSIONING_IDLE;
    bulb->commissioning.primary_channel_mask = ZIGBEE_PRIMARY_CHANNEL_MASK;
    bulb->commissioning.permit_join_seconds = ZIGBEE_PERMIT_JOIN_SECONDS;
    bulb->commissioning.factory_new = true;

    (void)zigbee_configure_security(bulb, default_tc_link_key);
}

static void zigbee_set_light_state(zigbee_light_bulb_t *bulb, bool on)
{
    if (bulb->on != on) {
        bulb->on = on;
        log_line("INFO", "Light state changed: %s", on ? "ON" : "OFF");
    }
}

static void zigbee_set_light_level(zigbee_light_bulb_t *bulb, uint8_t level)
{
    if (level < ZIGBEE_BULB_MIN_LEVEL) {
        level = ZIGBEE_BULB_MIN_LEVEL;
    } else if (level > ZIGBEE_BULB_MAX_LEVEL) {
        level = ZIGBEE_BULB_MAX_LEVEL;
    }

    if (bulb->level != level) {
        bulb->level = level;
        log_line("INFO", "Light level changed: %u", (unsigned)level);
    }
}

static bool zigbee_stack_initialize(zigbee_light_bulb_t *bulb)
{
    if (bulb == NULL) {
        return false;
    }

    bulb->commissioning_state = COMMISSIONING_INITIALIZATION;
    log_line("INFO", "Initializing Zigbee stack for smart light bulb endpoint %u", (unsigned)bulb->endpoint_id);
    log_line("INFO", "Primary channel mask: 0x%08" PRIX32, bulb->commissioning.primary_channel_mask);
    return true;
}

static bool zigbee_enable_permit_join(zigbee_light_bulb_t *bulb, uint16_t seconds)
{
    if (bulb == NULL || !bulb->network.joined) {
        return false;
    }

    bulb->network.permit_join = true;
    bulb->network.permit_join_deadline = time(NULL) + seconds;

    log_line("INFO", "permitJoin enabled for %u seconds on channel %u",
             (unsigned)seconds,
             (unsigned)bulb->network.current_channel);
    return true;
}

static bool zigbee_join_network_with_trust_center(zigbee_light_bulb_t *bulb)
{
    uint8_t channel;
    unsigned attempt;

    if (bulb == NULL || !bulb->security.use_trust_center_link_key) {
        return false;
    }

    bulb->commissioning_state = COMMISSIONING_NETWORK_STEERING;
    log_line("INFO", "Starting BDB network steering using trust center link key");

    for (attempt = 1; attempt <= ZIGBEE_MAX_JOIN_RETRIES; ++attempt) {
        channel = pick_channel_from_mask(bulb->commissioning.primary_channel_mask);
        if (channel == 0) {
            log_line("ERROR", "No valid Zigbee channels enabled in channel mask");
            return false;
        }

        log_line("INFO", "Join attempt %u/%u on channel %u", attempt, ZIGBEE_MAX_JOIN_RETRIES, (unsigned)channel);
        sleep_ms(750);

        if (attempt < 2) {
            log_line("WARN", "No suitable network found on channel %u, retrying", (unsigned)channel);
            continue;
        }

        bulb->network.joined = true;
        bulb->network.current_channel = channel;
        bulb->network.pan_id = (uint16_t)(0x1000U | (uint16_t)(rand() & 0x0FFF));
        bulb->network.short_address = (uint16_t)(0x0100U | (uint16_t)(rand() & 0x7EFF));
        bulb->network.extended_pan_id = random_u64();
        bulb->network.trust_center_ieee = 0x00124B0001ABCDEFULL;
        bulb->commissioning.factory_new = false;
        bulb->commissioning_state = COMMISSIONING_JOINED;

        log_line("INFO", "Joined Zigbee network successfully");
        log_line("INFO", "PAN ID: 0x%04" PRIX16 ", short address: 0x%04" PRIX16 ", extPAN: 0x%016" PRIX64,
                 bulb->network.pan_id,
                 bulb->network.short_address,
                 bulb->network.extended_pan_id);
        log_line("INFO", "Trust Center IEEE address: 0x%016" PRIX64, bulb->network.trust_center_ieee);

        return true;
    }

    log_line("ERROR", "Failed to join Zigbee network after %u attempts", ZIGBEE_MAX_JOIN_RETRIES);
    return false;
}

static bool zigbee_start_commissioning(zigbee_light_bulb_t *bulb)
{
    if (!zigbee_stack_initialize(bulb)) {
        return false;
    }

    if (!zigbee_join_network_with_trust_center(bulb)) {
        return false;
    }

    return zigbee_enable_permit_join(bulb, bulb->commissioning.permit_join_seconds);
}

static void zigbee_process_network_timers(zigbee_light_bulb_t *bulb)
{
    time_t now;

    if (bulb == NULL || !bulb->network.joined) {
        return;
    }

    now = time(NULL);

    if (bulb->network.permit_join && now >= bulb->network.permit_join_deadline) {
        bulb->network.permit_join = false;
        log_line("INFO", "permitJoin window closed");
    }
}

static void zigbee_print_status(const zigbee_light_bulb_t *bulb)
{
    long remaining = 0;

    if (bulb->network.permit_join) {
        remaining = (long)(bulb->network.permit_join_deadline - time(NULL));
        if (remaining < 0) {
            remaining = 0;
        }
    }

    log_line(
        "INFO",
        "Status: joined=%s channel=%u pan=0x%04" PRIX16 " short=0x%04" PRIX16 " light=%s level=%u permitJoin=%s remaining=%lds",
        bulb->network.joined ? "true" : "false",
        (unsigned)bulb->network.current_channel,
        bulb->network.pan_id,
        bulb->network.short_address,
        bulb->on ? "ON" : "OFF",
        (unsigned)bulb->level,
        bulb->network.permit_join ? "true" : "false",
        remaining
    );
}

int main(void)
{
    zigbee_light_bulb_t bulb;
    unsigned long heartbeat = 0;

    signal(SIGINT, handle_signal);
    signal(SIGTERM, handle_signal);

    srand((unsigned)time(NULL));

    zigbee_init_light_bulb(&bulb);

    if (!zigbee_start_commissioning(&bulb)) {
        log_line("ERROR", "Commissioning failed");
        return EXIT_FAILURE;
    }

    log_line("INFO", "Smart light bulb firmware is running");

    while (g_running) {
        zigbee_process_network_timers(&bulb);

        if (heartbeat == 2UL) {
            zigbee_set_light_state(&bulb, true);
        } else if (heartbeat == 4UL) {
            zigbee_set_light_level(&bulb, 192U);
        } else if (heartbeat == 6UL) {
            zigbee_set_light_level(&bulb, ZIGBEE_BULB_DEFAULT_LEVEL);
        }

        zigbee_print_status(&bulb);
        sleep_ms(1000);
        ++heartbeat;
    }

    log_line("INFO", "Shutting down smart light bulb firmware");
    return EXIT_SUCCESS;
}