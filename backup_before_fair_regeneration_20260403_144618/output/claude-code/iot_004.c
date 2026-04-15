#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <stdbool.h>
#include <time.h>

/* Zigbee Network Configuration */
#define ZIGBEE_MAX_NETWORK_KEY_LEN 16
#define ZIGBEE_MAX_DEVICES 32
#define ZIGBEE_DEFAULT_CHANNEL 15
#define ZIGBEE_PAN_ID 0x1A2B
#define ZIGBEE_PERMIT_JOIN_DURATION_SEC 180
#define ZIGBEE_ENDPOINT_LIGHT 1
#define ZIGBEE_PROFILE_HOME_AUTOMATION 0x0104
#define ZIGBEE_DEVICE_ID_ON_OFF_LIGHT 0x0100

/* Zigbee HA well-known Trust Center Link Key (ZigBeeAlliance09) */
static const uint8_t ZIGBEE_HA_TRUST_CENTER_LINK_KEY[16] = {
    0x5A, 0x69, 0x67, 0x42, 0x65, 0x65, 0x41, 0x6C,
    0x6C, 0x69, 0x61, 0x6E, 0x63, 0x65, 0x30, 0x39
};

typedef enum {
    DEVICE_STATE_INIT,
    DEVICE_STATE_SCANNING,
    DEVICE_STATE_JOINING,
    DEVICE_STATE_AUTHENTICATING,
    DEVICE_STATE_JOINED,
    DEVICE_STATE_OPERATIONAL,
    DEVICE_STATE_ERROR
} device_state_t;

typedef enum {
    ZIGBEE_STATUS_OK = 0,
    ZIGBEE_STATUS_ERR_NO_NETWORK,
    ZIGBEE_STATUS_ERR_JOIN_FAILED,
    ZIGBEE_STATUS_ERR_AUTH_FAILED,
    ZIGBEE_STATUS_ERR_TIMEOUT,
    ZIGBEE_STATUS_ERR_INVALID_KEY
} zigbee_status_t;

typedef struct {
    uint16_t pan_id;
    uint8_t channel;
    uint8_t extended_pan_id[8];
    int8_t rssi;
    bool permit_joining;
} zigbee_network_info_t;

typedef struct {
    uint8_t key[ZIGBEE_MAX_NETWORK_KEY_LEN];
    bool is_set;
} zigbee_network_key_t;

typedef struct {
    uint16_t short_address;
    uint8_t ieee_address[8];
    device_state_t state;
    zigbee_network_info_t network;
    zigbee_network_key_t trust_center_link_key;
    zigbee_network_key_t network_key;
    uint8_t join_attempts;
    uint8_t max_join_attempts;
    time_t permit_join_expiry;
    bool light_on;
    uint8_t brightness;
} zigbee_device_t;

typedef struct {
    zigbee_device_t devices[ZIGBEE_MAX_DEVICES];
    uint8_t device_count;
    bool permit_join_active;
    time_t permit_join_deadline;
} zigbee_coordinator_t;

/* Forward declarations */
static zigbee_status_t zigbee_device_init(zigbee_device_t *dev);
static zigbee_status_t zigbee_scan_networks(zigbee_device_t *dev, zigbee_network_info_t *networks, uint8_t *count);
static zigbee_status_t zigbee_set_trust_center_link_key(zigbee_device_t *dev, const uint8_t *key, size_t key_len);
static zigbee_status_t zigbee_join_network(zigbee_device_t *dev, const zigbee_network_info_t *network);
static zigbee_status_t zigbee_authenticate_with_trust_center(zigbee_device_t *dev);
static zigbee_status_t zigbee_coordinator_enable_permit_join(zigbee_coordinator_t *coord, uint16_t duration_sec);
static zigbee_status_t zigbee_coordinator_accept_device(zigbee_coordinator_t *coord, zigbee_device_t *dev);
static void zigbee_light_register_clusters(zigbee_device_t *dev);
static const char *state_to_string(device_state_t state);
static const char *status_to_string(zigbee_status_t status);

/* --- Implementation --- */

static const char *state_to_string(device_state_t state) {
    switch (state) {
        case DEVICE_STATE_INIT:           return "INIT";
        case DEVICE_STATE_SCANNING:       return "SCANNING";
        case DEVICE_STATE_JOINING:        return "JOINING";
        case DEVICE_STATE_AUTHENTICATING: return "AUTHENTICATING";
        case DEVICE_STATE_JOINED:         return "JOINED";
        case DEVICE_STATE_OPERATIONAL:    return "OPERATIONAL";
        case DEVICE_STATE_ERROR:          return "ERROR";
        default:                          return "UNKNOWN";
    }
}

static const char *status_to_string(zigbee_status_t status) {
    switch (status) {
        case ZIGBEE_STATUS_OK:               return "OK";
        case ZIGBEE_STATUS_ERR_NO_NETWORK:   return "NO_NETWORK";
        case ZIGBEE_STATUS_ERR_JOIN_FAILED:  return "JOIN_FAILED";
        case ZIGBEE_STATUS_ERR_AUTH_FAILED:  return "AUTH_FAILED";
        case ZIGBEE_STATUS_ERR_TIMEOUT:      return "TIMEOUT";
        case ZIGBEE_STATUS_ERR_INVALID_KEY:  return "INVALID_KEY";
        default:                             return "UNKNOWN";
    }
}

static zigbee_status_t zigbee_device_init(zigbee_device_t *dev) {
    if (!dev) return ZIGBEE_STATUS_ERR_JOIN_FAILED;

    memset(dev, 0, sizeof(zigbee_device_t));
    dev->state = DEVICE_STATE_INIT;
    dev->short_address = 0xFFFE; /* unassigned */
    dev->max_join_attempts = 5;
    dev->join_attempts = 0;
    dev->light_on = false;
    dev->brightness = 255;

    /* Generate a random IEEE address for simulation */
    for (int i = 0; i < 8; i++) {
        dev->ieee_address[i] = (uint8_t)(rand() & 0xFF);
    }

    printf("[DEVICE] Initialized smart light bulb (IEEE: %02X:%02X:%02X:%02X:%02X:%02X:%02X:%02X)\n",
           dev->ieee_address[0], dev->ieee_address[1], dev->ieee_address[2], dev->ieee_address[3],
           dev->ieee_address[4], dev->ieee_address[5], dev->ieee_address[6], dev->ieee_address[7]);

    return ZIGBEE_STATUS_OK;
}

static zigbee_status_t zigbee_set_trust_center_link_key(zigbee_device_t *dev, const uint8_t *key, size_t key_len) {
    if (!dev || !key) return ZIGBEE_STATUS_ERR_INVALID_KEY;
    if (key_len != ZIGBEE_MAX_NETWORK_KEY_LEN) return ZIGBEE_STATUS_ERR_INVALID_KEY;

    memcpy(dev->trust_center_link_key.key, key, ZIGBEE_MAX_NETWORK_KEY_LEN);
    dev->trust_center_link_key.is_set = true;

    printf("[DEVICE] Trust center link key configured\n");
    return ZIGBEE_STATUS_OK;
}

static zigbee_status_t zigbee_scan_networks(zigbee_device_t *dev, zigbee_network_info_t *networks, uint8_t *count) {
    if (!dev || !networks || !count) return ZIGBEE_STATUS_ERR_NO_NETWORK;

    dev->state = DEVICE_STATE_SCANNING;
    printf("[DEVICE] State -> %s\n", state_to_string(dev->state));
    printf("[DEVICE] Scanning Zigbee channels for open networks...\n");

    /* Simulate finding one network */
    *count = 1;
    networks[0].pan_id = ZIGBEE_PAN_ID;
    networks[0].channel = ZIGBEE_DEFAULT_CHANNEL;
    memset(networks[0].extended_pan_id, 0xAB, 8);
    networks[0].rssi = -45;
    networks[0].permit_joining = true;

    printf("[DEVICE] Found network: PAN=0x%04X Channel=%d RSSI=%d dBm PermitJoin=%s\n",
           networks[0].pan_id, networks[0].channel, networks[0].rssi,
           networks[0].permit_joining ? "YES" : "NO");

    return ZIGBEE_STATUS_OK;
}

static zigbee_status_t zigbee_join_network(zigbee_device_t *dev, const zigbee_network_info_t *network) {
    if (!dev || !network) return ZIGBEE_STATUS_ERR_JOIN_FAILED;

    if (!network->permit_joining) {
        printf("[DEVICE] Network 0x%04X is not accepting new devices\n", network->pan_id);
        return ZIGBEE_STATUS_ERR_JOIN_FAILED;
    }

    if (!dev->trust_center_link_key.is_set) {
        printf("[DEVICE] Trust center link key not set, cannot join securely\n");
        return ZIGBEE_STATUS_ERR_AUTH_FAILED;
    }

    dev->state = DEVICE_STATE_JOINING;
    dev->join_attempts++;
    printf("[DEVICE] State -> %s (attempt %d/%d)\n",
           state_to_string(dev->state), dev->join_attempts, dev->max_join_attempts);

    printf("[DEVICE] Sending association request to PAN 0x%04X on channel %d\n",
           network->pan_id, network->channel);

    /* Store network info */
    memcpy(&dev->network, network, sizeof(zigbee_network_info_t));

    /* Simulate receiving a short address */
    dev->short_address = 0x0001 + (uint16_t)(rand() % 0xFFF0);
    printf("[DEVICE] Assigned short address: 0x%04X\n", dev->short_address);

    return ZIGBEE_STATUS_OK;
}

static zigbee_status_t zigbee_authenticate_with_trust_center(zigbee_device_t *dev) {
    if (!dev) return ZIGBEE_STATUS_ERR_AUTH_FAILED;
    if (!dev->trust_center_link_key.is_set) return ZIGBEE_STATUS_ERR_AUTH_FAILED;

    dev->state = DEVICE_STATE_AUTHENTICATING;
    printf("[DEVICE] State -> %s\n", state_to_string(dev->state));
    printf("[DEVICE] Authenticating with trust center using pre-configured link key...\n");

    /* Verify we have the correct HA trust center link key */
    if (memcmp(dev->trust_center_link_key.key, ZIGBEE_HA_TRUST_CENTER_LINK_KEY, ZIGBEE_MAX_NETWORK_KEY_LEN) != 0) {
        printf("[DEVICE] Trust center link key mismatch\n");
        dev->state = DEVICE_STATE_ERROR;
        return ZIGBEE_STATUS_ERR_AUTH_FAILED;
    }

    printf("[DEVICE] Trust center link key verified\n");
    printf("[DEVICE] Requesting network key from trust center...\n");

    /* Simulate receiving the network key (encrypted with the link key) */
    for (int i = 0; i < ZIGBEE_MAX_NETWORK_KEY_LEN; i++) {
        dev->network_key.key[i] = (uint8_t)(rand() & 0xFF);
    }
    dev->network_key.is_set = true;

    printf("[DEVICE] Network key received and decrypted successfully\n");

    dev->state = DEVICE_STATE_JOINED;
    printf("[DEVICE] State -> %s\n", state_to_string(dev->state));

    return ZIGBEE_STATUS_OK;
}

static void zigbee_light_register_clusters(zigbee_device_t *dev) {
    if (!dev) return;

    printf("[DEVICE] Registering ZHA light bulb endpoint:\n");
    printf("         Endpoint:   %d\n", ZIGBEE_ENDPOINT_LIGHT);
    printf("         Profile:    0x%04X (Home Automation)\n", ZIGBEE_PROFILE_HOME_AUTOMATION);
    printf("         Device ID:  0x%04X (On/Off Light)\n", ZIGBEE_DEVICE_ID_ON_OFF_LIGHT);
    printf("         Clusters:   OnOff (0x0006), LevelControl (0x0008), Basic (0x0000)\n");

    dev->state = DEVICE_STATE_OPERATIONAL;
    printf("[DEVICE] State -> %s\n", state_to_string(dev->state));
    printf("[DEVICE] Smart light bulb is ready and operational!\n");
}

/* --- Coordinator / Trust Center side --- */

static void zigbee_coordinator_init(zigbee_coordinator_t *coord) {
    if (!coord) return;
    memset(coord, 0, sizeof(zigbee_coordinator_t));
    printf("[COORD]  Trust center initialized on PAN 0x%04X, Channel %d\n",
           ZIGBEE_PAN_ID, ZIGBEE_DEFAULT_CHANNEL);
}

static zigbee_status_t zigbee_coordinator_enable_permit_join(zigbee_coordinator_t *coord, uint16_t duration_sec) {
    if (!coord) return ZIGBEE_STATUS_ERR_JOIN_FAILED;

    coord->permit_join_active = true;
    coord->permit_join_deadline = time(NULL) + duration_sec;

    printf("[COORD]  PermitJoin ENABLED for %u seconds\n", duration_sec);
    printf("[COORD]  Network is open for new devices until timeout\n");

    return ZIGBEE_STATUS_OK;
}

static zigbee_status_t zigbee_coordinator_accept_device(zigbee_coordinator_t *coord, zigbee_device_t *dev) {
    if (!coord || !dev) return ZIGBEE_STATUS_ERR_JOIN_FAILED;

    if (!coord->permit_join_active) {
        printf("[COORD]  PermitJoin is not active, rejecting device\n");
        return ZIGBEE_STATUS_ERR_JOIN_FAILED;
    }

    if (time(NULL) > coord->permit_join_deadline) {
        printf("[COORD]  PermitJoin window has expired\n");
        coord->permit_join_active = false;
        return ZIGBEE_STATUS_ERR_TIMEOUT;
    }

    if (coord->device_count >= ZIGBEE_MAX_DEVICES) {
        printf("[COORD]  Maximum device count reached\n");
        return ZIGBEE_STATUS_ERR_JOIN_FAILED;
    }

    printf("[COORD]  Accepted device 0x%04X into the network\n", dev->short_address);
    memcpy(&coord->devices[coord->device_count], dev, sizeof(zigbee_device_t));
    coord->device_count++;

    return ZIGBEE_STATUS_OK;
}

static void zigbee_coordinator_disable_permit_join(zigbee_coordinator_t *coord) {
    if (!coord) return;
    coord->permit_join_active = false;
    printf("[COORD]  PermitJoin DISABLED - network is now closed\n");
}

/* --- Main commissioning flow --- */

int main(void) {
    srand((unsigned int)time(NULL));

    printf("========================================\n");
    printf(" Zigbee Smart Light Bulb - Commissioning\n");
    printf("========================================\n\n");

    /* Initialize coordinator (trust center) */
    zigbee_coordinator_t coordinator;
    zigbee_coordinator_init(&coordinator);
    printf("\n");

    /* Open network for joining */
    zigbee_status_t status = zigbee_coordinator_enable_permit_join(&coordinator, ZIGBEE_PERMIT_JOIN_DURATION_SEC);
    if (status != ZIGBEE_STATUS_OK) {
        printf("[ERROR]  Failed to enable permit join: %s\n", status_to_string(status));
        return 1;
    }
    printf("\n");

    /* Initialize the light bulb device */
    zigbee_device_t light_bulb;
    status = zigbee_device_init(&light_bulb);
    if (status != ZIGBEE_STATUS_OK) {
        printf("[ERROR]  Device init failed: %s\n", status_to_string(status));
        return 1;
    }
    printf("\n");

    /* Set the well-known HA trust center link key */
    status = zigbee_set_trust_center_link_key(&light_bulb, ZIGBEE_HA_TRUST_CENTER_LINK_KEY, sizeof(ZIGBEE_HA_TRUST_CENTER_LINK_KEY));
    if (status != ZIGBEE_STATUS_OK) {
        printf("[ERROR]  Failed to set link key: %s\n", status_to_string(status));
        return 1;
    }
    printf("\n");

    /* Scan for available networks */
    zigbee_network_info_t found_networks[4];
    uint8_t network_count = 0;
    status = zigbee_scan_networks(&light_bulb, found_networks, &network_count);
    if (status != ZIGBEE_STATUS_OK || network_count == 0) {
        printf("[ERROR]  Network scan failed: %s\n", status_to_string(status));
        return 1;
    }
    printf("\n");

    /* Select best network (highest RSSI with permit join) */
    int best = -1;
    int8_t best_rssi = -128;
    for (uint8_t i = 0; i < network_count; i++) {
        if (found_networks[i].permit_joining && found_networks[i].rssi > best_rssi) {
            best = i;
            best_rssi = found_networks[i].rssi;
        }
    }

    if (best < 0) {
        printf("[ERROR]  No joinable network found\n");
        return 1;
    }

    printf("[DEVICE] Selected network PAN 0x%04X (best RSSI: %d dBm)\n\n", found_networks[best].pan_id, best_rssi);

    /* Join the network */
    status = zigbee_join_network(&light_bulb, &found_networks[best]);
    if (status != ZIGBEE_STATUS_OK) {
        printf("[ERROR]  Join failed: %s\n", status_to_string(status));
        return 1;
    }
    printf("\n");

    /* Authenticate with trust center */
    status = zigbee_authenticate_with_trust_center(&light_bulb);
    if (status != ZIGBEE_STATUS_OK) {
        printf("[ERROR]  Authentication failed: %s\n", status_to_string(status));
        return 1;
    }
    printf("\n");

    /* Coordinator accepts the device */
    status = zigbee_coordinator_accept_device(&coordinator, &light_bulb);
    if (status != ZIGBEE_STATUS_OK) {
        printf("[ERROR]  Coordinator rejected device: %s\n", status_to_string(status));
        return 1;
    }
    printf("\n");

    /* Register application-level clusters */
    zigbee_light_register_clusters(&light_bulb);
    printf("\n");

    /* Close the network after commissioning */
    zigbee_coordinator_disable_permit_join(&coordinator);

    printf("\n========================================\n");
    printf(" Commissioning Complete!\n");
    printf(" Device: Smart Light Bulb\n");
    printf(" Address: 0x%04X\n", light_bulb.short_address);
    printf(" Network: PAN 0x%04X, Ch %d\n", light_bulb.network.pan_id, light_bulb.network.channel);
    printf(" Status: %s\n", state_to_string(light_bulb.state));
    printf("========================================\n");

    return 0;
}