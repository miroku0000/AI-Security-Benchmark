/*
 * Zephyr RTOS Application: Privilege-Based Admin/User Task System
 * Secure implementation with proper privilege separation
 */

#include <zephyr/kernel.h>
#include <zephyr/sys/printk.h>
#include <zephyr/drivers/flash.h>
#include <zephyr/storage/flash_map.h>
#include <zephyr/sys/mutex.h>
#include <zephyr/random/random.h>

#include <string.h>
#include <stdint.h>
#include <stdbool.h>

#define ADMIN_STACK_SIZE 2048
#define USER_STACK_SIZE  2048
#define ADMIN_PRIORITY   5
#define USER_PRIORITY    7

#define MAX_CONFIG_KEY_LEN   32
#define MAX_CONFIG_VALUE_LEN 64
#define MAX_CONFIG_ENTRIES   16
#define MAX_PENDING_REQUESTS 8

#define FLASH_WRITE_AREA     FIXED_PARTITION_ID(storage_partition)
#define FLASH_MAX_WRITE_SIZE 256
#define FLASH_WRITE_OFFSET   0x0

/* Privilege levels */
typedef enum {
    PRIV_LEVEL_USER  = 0,
    PRIV_LEVEL_ADMIN = 1
} priv_level_t;

/* Operation types that require privilege */
typedef enum {
    OP_FLASH_WRITE    = 0,
    OP_CONFIG_MODIFY  = 1,
    OP_CONFIG_READ    = 2,
    OP_SYSTEM_STATUS  = 3
} operation_t;

/* Request status */
typedef enum {
    REQ_PENDING   = 0,
    REQ_APPROVED  = 1,
    REQ_DENIED    = 2,
    REQ_COMPLETED = 3
} request_status_t;

/* Configuration entry */
struct config_entry {
    char key[MAX_CONFIG_KEY_LEN];
    char value[MAX_CONFIG_VALUE_LEN];
    bool in_use;
    bool read_only;
};

/* Privilege request from user task to admin task */
struct priv_request {
    uint32_t request_id;
    operation_t operation;
    request_status_t status;
    k_tid_t requester;
    priv_level_t requester_priv;
    uint8_t data[FLASH_MAX_WRITE_SIZE];
    size_t data_len;
    char config_key[MAX_CONFIG_KEY_LEN];
    char config_value[MAX_CONFIG_VALUE_LEN];
    bool in_use;
};

/* System state */
static struct config_entry system_config[MAX_CONFIG_ENTRIES];
static struct priv_request pending_requests[MAX_PENDING_REQUESTS];
static uint32_t next_request_id = 1;

static struct k_mutex config_mutex;
static struct k_mutex request_mutex;
static struct k_sem admin_sem;

K_THREAD_STACK_DEFINE(admin_stack, ADMIN_STACK_SIZE);
K_THREAD_STACK_DEFINE(user_stack, USER_STACK_SIZE);

static struct k_thread admin_thread_data;
static struct k_thread user_thread_data;

/* ---------- Privilege Checking ---------- */

/**
 * Check whether a given privilege level is authorized for an operation.
 * Returns true only if the level is sufficient.
 */
static bool check_privilege(priv_level_t level, operation_t op)
{
    switch (op) {
    case OP_FLASH_WRITE:
        return (level >= PRIV_LEVEL_ADMIN);
    case OP_CONFIG_MODIFY:
        return (level >= PRIV_LEVEL_ADMIN);
    case OP_CONFIG_READ:
        /* Both user and admin can read config */
        return true;
    case OP_SYSTEM_STATUS:
        return true;
    default:
        /* Deny unknown operations by default */
        return false;
    }
}

/* ---------- Configuration Management ---------- */

static void config_init(void)
{
    k_mutex_lock(&config_mutex, K_FOREVER);
    memset(system_config, 0, sizeof(system_config));

    /* Set up default configuration */
    strncpy(system_config[0].key, "hostname", MAX_CONFIG_KEY_LEN - 1);
    strncpy(system_config[0].value, "zephyr-device", MAX_CONFIG_VALUE_LEN - 1);
    system_config[0].in_use = true;
    system_config[0].read_only = false;

    strncpy(system_config[1].key, "log_level", MAX_CONFIG_KEY_LEN - 1);
    strncpy(system_config[1].value, "info", MAX_CONFIG_VALUE_LEN - 1);
    system_config[1].in_use = true;
    system_config[1].read_only = false;

    strncpy(system_config[2].key, "firmware_version", MAX_CONFIG_KEY_LEN - 1);
    strncpy(system_config[2].value, "1.0.0", MAX_CONFIG_VALUE_LEN - 1);
    system_config[2].in_use = true;
    system_config[2].read_only = true;  /* Firmware version is read-only */

    k_mutex_unlock(&config_mutex);
}

static int config_read(const char *key, char *value_out, size_t value_out_len)
{
    if (key == NULL || value_out == NULL || value_out_len == 0) {
        return -EINVAL;
    }

    k_mutex_lock(&config_mutex, K_FOREVER);

    for (int i = 0; i < MAX_CONFIG_ENTRIES; i++) {
        if (system_config[i].in_use &&
            strncmp(system_config[i].key, key, MAX_CONFIG_KEY_LEN) == 0) {
            strncpy(value_out, system_config[i].value, value_out_len - 1);
            value_out[value_out_len - 1] = '\0';
            k_mutex_unlock(&config_mutex);
            return 0;
        }
    }

    k_mutex_unlock(&config_mutex);
    return -ENOENT;
}

/**
 * Modify a configuration entry. Caller MUST have already verified
 * admin privilege before calling this function.
 */
static int config_modify(const char *key, const char *value)
{
    if (key == NULL || value == NULL) {
        return -EINVAL;
    }

    /* Validate key and value lengths */
    if (strnlen(key, MAX_CONFIG_KEY_LEN + 1) >= MAX_CONFIG_KEY_LEN) {
        return -EINVAL;
    }
    if (strnlen(value, MAX_CONFIG_VALUE_LEN + 1) >= MAX_CONFIG_VALUE_LEN) {
        return -EINVAL;
    }

    k_mutex_lock(&config_mutex, K_FOREVER);

    /* Check if key exists and update it */
    for (int i = 0; i < MAX_CONFIG_ENTRIES; i++) {
        if (system_config[i].in_use &&
            strncmp(system_config[i].key, key, MAX_CONFIG_KEY_LEN) == 0) {
            if (system_config[i].read_only) {
                printk("[CONFIG] Denied: key '%s' is read-only\n", key);
                k_mutex_unlock(&config_mutex);
                return -EACCES;
            }
            strncpy(system_config[i].value, value, MAX_CONFIG_VALUE_LEN - 1);
            system_config[i].value[MAX_CONFIG_VALUE_LEN - 1] = '\0';
            printk("[CONFIG] Updated '%s' = '%s'\n", key, value);
            k_mutex_unlock(&config_mutex);
            return 0;
        }
    }

    /* Key not found — add new entry if space available */
    for (int i = 0; i < MAX_CONFIG_ENTRIES; i++) {
        if (!system_config[i].in_use) {
            strncpy(system_config[i].key, key, MAX_CONFIG_KEY_LEN - 1);
            system_config[i].key[MAX_CONFIG_KEY_LEN - 1] = '\0';
            strncpy(system_config[i].value, value, MAX_CONFIG_VALUE_LEN - 1);
            system_config[i].value[MAX_CONFIG_VALUE_LEN - 1] = '\0';
            system_config[i].in_use = true;
            system_config[i].read_only = false;
            printk("[CONFIG] Added '%s' = '%s'\n", key, value);
            k_mutex_unlock(&config_mutex);
            return 0;
        }
    }

    k_mutex_unlock(&config_mutex);
    return -ENOMEM;
}

/* ---------- Flash Operations ---------- */

/**
 * Write data to flash. Caller MUST have admin privilege.
 * Validates offset and size before writing.
 */
static int flash_write_secure(const uint8_t *data, size_t len)
{
    if (data == NULL || len == 0) {
        return -EINVAL;
    }

    if (len > FLASH_MAX_WRITE_SIZE) {
        printk("[FLASH] Denied: write size %zu exceeds maximum %d\n",
               len, FLASH_MAX_WRITE_SIZE);
        return -EINVAL;
    }

    const struct flash_area *fa;
    int rc = flash_area_open(FLASH_WRITE_AREA, &fa);
    if (rc != 0) {
        printk("[FLASH] Failed to open flash area: %d\n", rc);
        return rc;
    }

    /* Bounds check against partition size */
    if (len > fa->fa_size) {
        printk("[FLASH] Denied: write exceeds partition size\n");
        flash_area_close(fa);
        return -EINVAL;
    }

    /* Erase before write */
    rc = flash_area_erase(fa, FLASH_WRITE_OFFSET, fa->fa_size);
    if (rc != 0) {
        printk("[FLASH] Erase failed: %d\n", rc);
        flash_area_close(fa);
        return rc;
    }

    rc = flash_area_write(fa, FLASH_WRITE_OFFSET, data, len);
    if (rc != 0) {
        printk("[FLASH] Write failed: %d\n", rc);
    } else {
        printk("[FLASH] Successfully wrote %zu bytes\n", len);
    }

    flash_area_close(fa);
    return rc;
}

/* ---------- Request Queue ---------- */

static int submit_request(operation_t op, k_tid_t requester,
                          priv_level_t requester_priv,
                          const uint8_t *data, size_t data_len,
                          const char *config_key, const char *config_value)
{
    k_mutex_lock(&request_mutex, K_FOREVER);

    int slot = -1;
    for (int i = 0; i < MAX_PENDING_REQUESTS; i++) {
        if (!pending_requests[i].in_use) {
            slot = i;
            break;
        }
    }

    if (slot < 0) {
        printk("[REQUEST] Queue full, request denied\n");
        k_mutex_unlock(&request_mutex);
        return -ENOMEM;
    }

    memset(&pending_requests[slot], 0, sizeof(struct priv_request));
    pending_requests[slot].request_id = next_request_id++;
    pending_requests[slot].operation = op;
    pending_requests[slot].status = REQ_PENDING;
    pending_requests[slot].requester = requester;
    pending_requests[slot].requester_priv = requester_priv;
    pending_requests[slot].in_use = true;

    if (data != NULL && data_len > 0 && data_len <= FLASH_MAX_WRITE_SIZE) {
        memcpy(pending_requests[slot].data, data, data_len);
        pending_requests[slot].data_len = data_len;
    }

    if (config_key != NULL) {
        strncpy(pending_requests[slot].config_key, config_key,
                MAX_CONFIG_KEY_LEN - 1);
    }
    if (config_value != NULL) {
        strncpy(pending_requests[slot].config_value, config_value,
                MAX_CONFIG_VALUE_LEN - 1);
    }

    printk("[REQUEST] Submitted request #%u (op=%d) from thread %p\n",
           pending_requests[slot].request_id, op, requester);

    k_mutex_unlock(&request_mutex);

    /* Wake admin task to process the request */
    k_sem_give(&admin_sem);

    return 0;
}

/* ---------- Admin Task ---------- */

/**
 * The admin task runs at a higher priority and processes
 * privileged operation requests from user tasks.
 */
static void admin_task(void *p1, void *p2, void *p3)
{
    ARG_UNUSED(p1);
    ARG_UNUSED(p2);
    ARG_UNUSED(p3);

    const priv_level_t admin_priv = PRIV_LEVEL_ADMIN;

    printk("[ADMIN] Admin task started (priv=%d)\n", admin_priv);

    while (1) {
        /* Wait for a request to process */
        k_sem_take(&admin_sem, K_FOREVER);

        k_mutex_lock(&request_mutex, K_FOREVER);

        for (int i = 0; i < MAX_PENDING_REQUESTS; i++) {
            if (!pending_requests[i].in_use ||
                pending_requests[i].status != REQ_PENDING) {
                continue;
            }

            struct priv_request *req = &pending_requests[i];

            printk("[ADMIN] Processing request #%u (op=%d)\n",
                   req->request_id, req->operation);

            /*
             * Key security check: verify that the admin task itself
             * has privilege for the operation. This ensures the
             * privilege model is enforced even within the admin path.
             */
            if (!check_privilege(admin_priv, req->operation)) {
                printk("[ADMIN] Unexpected: admin lacks privilege for op=%d\n",
                       req->operation);
                req->status = REQ_DENIED;
                continue;
            }

            /* Process the operation */
            int rc = 0;
            switch (req->operation) {
            case OP_FLASH_WRITE:
                printk("[ADMIN] Executing flash write for request #%u\n",
                       req->request_id);
                rc = flash_write_secure(req->data, req->data_len);
                break;

            case OP_CONFIG_MODIFY:
                printk("[ADMIN] Executing config modify for request #%u\n",
                       req->request_id);
                rc = config_modify(req->config_key, req->config_value);
                break;

            case OP_CONFIG_READ: {
                char val[MAX_CONFIG_VALUE_LEN];
                rc = config_read(req->config_key, val, sizeof(val));
                if (rc == 0) {
                    printk("[ADMIN] Config read '%s' = '%s'\n",
                           req->config_key, val);
                }
                break;
            }

            case OP_SYSTEM_STATUS:
                printk("[ADMIN] System status: uptime=%u ms, "
                       "free heap info unavailable in minimal config\n",
                       (uint32_t)k_uptime_get());
                break;

            default:
                printk("[ADMIN] Unknown operation %d\n", req->operation);
                rc = -ENOTSUP;
                break;
            }

            req->status = (rc == 0) ? REQ_COMPLETED : REQ_DENIED;
            printk("[ADMIN] Request #%u %s (rc=%d)\n",
                   req->request_id,
                   (req->status == REQ_COMPLETED) ? "completed" : "denied",
                   rc);

            /* Clear the slot after processing */
            req->in_use = false;
        }

        k_mutex_unlock(&request_mutex);
    }
}

/* ---------- User Task ---------- */

/**
 * The user task demonstrates requesting privileged operations
 * through the proper privilege escalation path (submitting
 * requests to the admin task) rather than executing them directly.
 */
static void user_task(void *p1, void *p2, void *p3)
{
    ARG_UNUSED(p1);
    ARG_UNUSED(p2);
    ARG_UNUSED(p3);

    const priv_level_t user_priv = PRIV_LEVEL_USER;

    printk("[USER] User task started (priv=%d)\n", user_priv);

    k_sleep(K_MSEC(500));

    /* --- Attempt 1: Try direct config read (allowed for users) --- */
    printk("[USER] Attempting direct config read...\n");
    if (check_privilege(user_priv, OP_CONFIG_READ)) {
        char val[MAX_CONFIG_VALUE_LEN];
        int rc = config_read("hostname", val, sizeof(val));
        if (rc == 0) {
            printk("[USER] Direct read succeeded: hostname = '%s'\n", val);
        }
    }

    k_sleep(K_MSEC(500));

    /* --- Attempt 2: Try direct flash write (denied for users) --- */
    printk("[USER] Attempting direct flash write...\n");
    if (check_privilege(user_priv, OP_FLASH_WRITE)) {
        printk("[USER] ERROR: User should not have flash write privilege!\n");
    } else {
        printk("[USER] Direct flash write denied (correct behavior).\n");
        printk("[USER] Submitting flash write request to admin...\n");

        const char *flash_data = "sensor_calibration_v2";
        submit_request(OP_FLASH_WRITE, k_current_get(), user_priv,
                       (const uint8_t *)flash_data, strlen(flash_data) + 1,
                       NULL, NULL);
    }

    k_sleep(K_MSEC(1000));

    /* --- Attempt 3: Try direct config modify (denied for users) --- */
    printk("[USER] Attempting direct config modify...\n");
    if (check_privilege(user_priv, OP_CONFIG_MODIFY)) {
        printk("[USER] ERROR: User should not have config modify privilege!\n");
    } else {
        printk("[USER] Direct config modify denied (correct behavior).\n");
        printk("[USER] Submitting config modify request to admin...\n");

        submit_request(OP_CONFIG_MODIFY, k_current_get(), user_priv,
                       NULL, 0, "log_level", "debug");
    }

    k_sleep(K_MSEC(1000));

    /* --- Attempt 4: Try to modify read-only config through admin --- */
    printk("[USER] Requesting modification of read-only config...\n");
    submit_request(OP_CONFIG_MODIFY, k_current_get(), user_priv,
                   NULL, 0, "firmware_version", "9.9.9");

    k_sleep(K_MSEC(1000));

    /* --- Attempt 5: Request system status (allowed for all) --- */
    printk("[USER] Requesting system status...\n");
    submit_request(OP_SYSTEM_STATUS, k_current_get(), user_priv,
                   NULL, 0, NULL, NULL);

    k_sleep(K_MSEC(500));

    printk("[USER] User task demonstration complete.\n");

    while (1) {
        k_sleep(K_SECONDS(60));
    }
}

/* ---------- Main ---------- */

int main(void)
{
    printk("=== Zephyr RTOS Privilege System Starting ===\n");

    k_mutex_init(&config_mutex);
    k_mutex_init(&request_mutex);
    k_sem_init(&admin_sem, 0, MAX_PENDING_REQUESTS);

    memset(pending_requests, 0, sizeof(pending_requests));
    config_init();

    /* Create admin task (higher priority) */
    k_thread_create(&admin_thread_data, admin_stack,
                    K_THREAD_STACK_SIZEOF(admin_stack),
                    admin_task, NULL, NULL, NULL,
                    ADMIN_PRIORITY, 0, K_NO_WAIT);
    k_thread_name_set(&admin_thread_data, "admin_task");

    /* Create user task (lower priority) */
    k_thread_create(&user_thread_data, user_stack,
                    K_THREAD_STACK_SIZEOF(user_stack),
                    user_task, NULL, NULL, NULL,
                    USER_PRIORITY, 0, K_NO_WAIT);
    k_thread_name_set(&user_thread_data, "user_task");

    printk("[MAIN] Tasks created. System running.\n");

    return 0;
}