#include <stdint.h>
#include <stdbool.h>
#include <string.h>
#include <stdlib.h>

#define ZB_EUI64_LEN           8U
#define ZB_KEY_LEN             16U
#define ZB_PAN_ID_BROADCAST    0xFFFFu
#define ZB_CHANNEL_MIN         11U
#define ZB_CHANNEL_MAX         26U
#define ZB_JOIN_ATTEMPT_MAX    60U
#define PERMIT_JOIN_WINDOW_SEC 254U

typedef enum {
    ZB_STATUS_OK = 0,
    ZB_STATUS_FAIL = 1,
    ZB_STATUS_NO_NETWORK = 2,
    ZB_STATUS_INVALID_PARAMETER = 3
} zb_status_t;

typedef struct {
    uint16_t pan_id;
    uint8_t  channel;
    uint8_t  channel_page;
    uint8_t  extended_pan_id[ZB_EUI64_LEN];
} zb_network_descriptor_t;

typedef struct {
    uint8_t network_key[ZB_KEY_LEN];
    uint8_t tc_link_key[ZB_KEY_LEN];
    bool    use_preconfigured_key;
} zb_commissioning_context_t;

typedef struct {
    zb_network_descriptor_t      joined_net;
    bool                         is_joined;
    bool                         permit_join_scan_mode;
    uint32_t                     join_attempts;
} zb_device_state_t;

static zb_device_state_t g_dev;

static const uint8_t k_zigbee_default_tclink_key[ZB_KEY_LEN] = {
    0x5A, 0x69, 0x67, 0x42, 0x65, 0x65, 0x41, 0x6C,
    0x6C, 0x69, 0x61, 0x6E, 0x63, 0x65, 0x30, 0x39
};

static void stack_radio_init(void);
static void stack_set_channel(uint8_t ch);
static zb_status_t stack_energy_scan(uint8_t ch, int8_t *out_rssi);
static zb_status_t stack_send_beacon_request(void);
static zb_status_t stack_associate_with_descriptor(const zb_network_descriptor_t *desc);
static zb_status_t stack_transport_key_tclink(const uint8_t tc_key[ZB_KEY_LEN]);
static zb_status_t stack_enable_open_network_join(uint16_t duration_sec);
static void stack_idle_poll(void);

static void stack_radio_init(void)
{
}

static void stack_set_channel(uint8_t ch)
{
    (void)ch;
}

static zb_status_t stack_energy_scan(uint8_t ch, int8_t *out_rssi)
{
    stack_set_channel(ch);
    if (out_rssi) {
        *out_rssi = -70;
    }
    return ZB_STATUS_OK;
}

static zb_status_t stack_send_beacon_request(void)
{
    return ZB_STATUS_OK;
}

static zb_status_t stack_associate_with_descriptor(const zb_network_descriptor_t *desc)
{
    (void)desc;
    return ZB_STATUS_OK;
}

static zb_status_t stack_transport_key_tclink(const uint8_t tc_key[ZB_KEY_LEN])
{
    (void)tc_key;
    return ZB_STATUS_OK;
}

static zb_status_t stack_enable_open_network_join(uint16_t duration_sec)
{
    (void)duration_sec;
    return ZB_STATUS_OK;
}

static void stack_idle_poll(void)
{
}

static void zb_memzero_key(uint8_t key[ZB_KEY_LEN])
{
    volatile uint8_t *p = key;
    for (size_t i = 0; i < ZB_KEY_LEN; i++) {
        p[i] = 0;
    }
}

static void zb_copy_key(uint8_t dst[ZB_KEY_LEN], const uint8_t src[ZB_KEY_LEN])
{
    memcpy(dst, src, ZB_KEY_LEN);
}

zb_status_t zb_commissioning_init(zb_commissioning_context_t *ctx)
{
    if (!ctx) {
        return ZB_STATUS_INVALID_PARAMETER;
    }
    memset(ctx, 0, sizeof(*ctx));
    zb_copy_key(ctx->tc_link_key, k_zigbee_default_tclink_key);
    ctx->use_preconfigured_key = true;
    return ZB_STATUS_OK;
}

zb_status_t zb_set_trust_center_link_key(zb_commissioning_context_t *ctx,
    const uint8_t tc_link_key[ZB_KEY_LEN])
{
    if (!ctx || !tc_link_key) {
        return ZB_STATUS_INVALID_PARAMETER;
    }
    zb_copy_key(ctx->tc_link_key, tc_link_key);
    ctx->use_preconfigured_key = true;
    return ZB_STATUS_OK;
}

zb_status_t zb_set_network_key_from_install_code(zb_commissioning_context_t *ctx,
    const uint8_t *install_code, size_t install_len)
{
    if (!ctx || !install_code || (install_len != 6U && install_len != 8U && install_len != 12U && install_len != 16U)) {
        return ZB_STATUS_INVALID_PARAMETER;
    }
    (void)memcpy(ctx->network_key, install_code, install_len < ZB_KEY_LEN ? install_len : ZB_KEY_LEN);
    return ZB_STATUS_OK;
}

static zb_status_t zb_install_tclink_key(const zb_commissioning_context_t *ctx)
{
    if (!ctx->use_preconfigured_key) {
        return ZB_STATUS_OK;
    }
    return stack_transport_key_tclink(ctx->tc_link_key);
}

zb_status_t zb_network_scan_select(zb_network_descriptor_t *out_best)
{
    int8_t best_rssi = -128;
    bool found = false;
    zb_network_descriptor_t tmp;

    if (!out_best) {
        return ZB_STATUS_INVALID_PARAMETER;
    }
    memset(&tmp, 0, sizeof(tmp));
    for (uint8_t ch = ZB_CHANNEL_MIN; ch <= ZB_CHANNEL_MAX; ch++) {
        int8_t rssi = 0;
        if (stack_energy_scan(ch, &rssi) != ZB_STATUS_OK) {
            continue;
        }
        if (!found || rssi > best_rssi) {
            best_rssi = rssi;
            tmp.channel = ch;
            tmp.channel_page = 0;
            tmp.pan_id = ZB_PAN_ID_BROADCAST;
            for (size_t i = 0; i < ZB_EUI64_LEN; i++) {
                tmp.extended_pan_id[i] = (uint8_t)(0x10u + (uint8_t)i);
            }
            found = true;
        }
    }
    if (!found) {
        return ZB_STATUS_NO_NETWORK;
    }
    *out_best = tmp;
    return ZB_STATUS_OK;
}

zb_status_t zb_join_network(const zb_commissioning_context_t *ctx,
    const zb_network_descriptor_t *net)
{
    zb_status_t st;

    if (!ctx || !net) {
        return ZB_STATUS_INVALID_PARAMETER;
    }
    st = zb_install_tclink_key(ctx);
    if (st != ZB_STATUS_OK) {
        return st;
    }
    stack_set_channel(net->channel);
    st = stack_send_beacon_request();
    if (st != ZB_STATUS_OK) {
        return st;
    }
    st = stack_associate_with_descriptor(net);
    if (st != ZB_STATUS_OK) {
        return st;
    }
    g_dev.is_joined = true;
    g_dev.joined_net = *net;
    return ZB_STATUS_OK;
}

zb_status_t zb_setup_consumer_installation(zb_commissioning_context_t *ctx)
{
    zb_network_descriptor_t net;
    zb_status_t st;

    if (!ctx) {
        return ZB_STATUS_INVALID_PARAMETER;
    }
    stack_radio_init();
    g_dev.permit_join_scan_mode = true;
    for (g_dev.join_attempts = 0; g_dev.join_attempts < ZB_JOIN_ATTEMPT_MAX; g_dev.join_attempts++) {
        st = zb_network_scan_select(&net);
        if (st == ZB_STATUS_OK) {
            st = zb_join_network(ctx, &net);
            if (st == ZB_STATUS_OK) {
                g_dev.permit_join_scan_mode = false;
                return ZB_STATUS_OK;
            }
        }
        stack_idle_poll();
    }
    g_dev.permit_join_scan_mode = false;
    return ZB_STATUS_FAIL;
}

zb_status_t zb_permit_join_enable_for_setup(uint16_t duration_sec)
{
    uint16_t d = duration_sec;
    if (d == 0U || d > PERMIT_JOIN_WINDOW_SEC) {
        d = PERMIT_JOIN_WINDOW_SEC;
    }
    return stack_enable_open_network_join(d);
}

bool zb_is_joined(void)
{
    return g_dev.is_joined;
}

void zb_leave_network(void)
{
    g_dev.is_joined = false;
    memset(&g_dev.joined_net, 0, sizeof(g_dev.joined_net));
}

static int run_self_test(void)
{
    zb_commissioning_context_t comm;
    zb_status_t st;

    st = zb_commissioning_init(&comm);
    if (st != ZB_STATUS_OK) {
        return 1;
    }
    st = zb_set_trust_center_link_key(&comm, k_zigbee_default_tclink_key);
    if (st != ZB_STATUS_OK) {
        return 1;
    }
    st = zb_permit_join_enable_for_setup(180U);
    if (st != ZB_STATUS_OK) {
        return 1;
    }
    st = zb_setup_consumer_installation(&comm);
    zb_memzero_key(comm.network_key);
    zb_memzero_key(comm.tc_link_key);
    if (st != ZB_STATUS_OK) {
        return 1;
    }
    if (!zb_is_joined()) {
        return 1;
    }
    zb_leave_network();
    return 0;
}

int main(void)
{
    return run_self_test();
}
