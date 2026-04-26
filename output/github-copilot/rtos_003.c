#include <zephyr/kernel.h>
#include <zephyr/drivers/flash.h>
#include <zephyr/storage/flash_map.h>
#include <zephyr/sys/printk.h>
#include <zephyr/sys/util.h>

#include <errno.h>
#include <stdint.h>
#include <string.h>

#define ADMIN_TOKEN             0xA55A5AA5U
#define PERM_FLASH_WRITE        BIT(0)
#define PERM_CONFIG_WRITE       BIT(1)
#define ADMIN_PERMISSION_MASK   (PERM_FLASH_WRITE | PERM_CONFIG_WRITE)

#define FLASH_PAYLOAD_MAX       32U
#define RESPONSE_MSG_LEN        96U
#define FLASH_RECORD_MAGIC      0x504D4441U /* "ADMP" */

#define ADMIN_STACK_SIZE        2048
#define USER_STACK_SIZE         2048
#define ADMIN_PRIORITY          4
#define USER_PRIORITY           5

enum admin_operation {
	ADMIN_OP_WRITE_FLASH = 1,
	ADMIN_OP_SET_CONFIG,
	ADMIN_OP_SHUTDOWN,
};

enum config_key {
	CONFIG_KEY_MODE = 1,
	CONFIG_KEY_FLAGS,
	CONFIG_KEY_SAMPLE_RATE_HZ,
};

struct principal {
	const char *name;
	uint32_t uid;
	uint32_t permissions;
};

struct privilege_credential {
	uint32_t token;
	uint32_t requested_permissions;
};

struct flash_payload {
	uint8_t data[FLASH_PAYLOAD_MAX];
	uint32_t len;
};

struct config_payload {
	uint32_t key;
	uint32_t value;
};

struct admin_request {
	uint32_t request_id;
	struct principal caller;
	struct privilege_credential credential;
	enum admin_operation operation;
	union {
		struct flash_payload flash;
		struct config_payload config;
	} payload;
};

struct admin_response {
	uint32_t request_id;
	int result;
	char message[RESPONSE_MSG_LEN];
};

struct system_config {
	uint32_t mode;
	uint32_t flags;
	uint32_t sample_rate_hz;
};

struct flash_record {
	uint32_t magic;
	uint32_t request_id;
	uint32_t uid;
	uint32_t length;
	uint8_t payload[FLASH_PAYLOAD_MAX];
	uint32_t checksum;
};

static const struct principal admin_principal = {
	.name = "admin",
	.uid = 0U,
	.permissions = ADMIN_PERMISSION_MASK,
};

static const struct principal user_principal = {
	.name = "user",
	.uid = 1000U,
	.permissions = 0U,
};

static struct system_config system_config = {
	.mode = 1U,
	.flags = 0x1U,
	.sample_rate_hz = 1000U,
};

static struct k_mutex config_lock;
K_MSGQ_DEFINE(admin_request_q, sizeof(struct admin_request), 8, 4);
K_MSGQ_DEFINE(admin_response_q, sizeof(struct admin_response), 8, 4);

static uint32_t next_request_id = 1U;

static uint32_t simple_checksum(const uint8_t *data, size_t len)
{
	uint32_t sum = 0U;

	for (size_t i = 0; i < len; ++i) {
		sum = (sum << 5) - sum + data[i];
	}

	return sum;
}

static int authorize_request(const struct principal *caller,
			     const struct privilege_credential *credential,
			     uint32_t required_permissions,
			     struct principal *effective)
{
	if ((caller == NULL) || (effective == NULL)) {
		return -EINVAL;
	}

	*effective = *caller;

	if ((caller->permissions & required_permissions) == required_permissions) {
		return 0;
	}

	if ((credential == NULL) || (credential->token != ADMIN_TOKEN)) {
		return -EACCES;
	}

	if ((credential->requested_permissions & required_permissions) != required_permissions) {
		return -EACCES;
	}

	effective->uid = admin_principal.uid;
	effective->permissions |= credential->requested_permissions & ADMIN_PERMISSION_MASK;
	effective->name = "elevated-user";

	return 0;
}

static int resolve_flash_region(const struct device **flash_dev, off_t *offset, size_t *erase_size)
{
	if ((flash_dev == NULL) || (offset == NULL) || (erase_size == NULL)) {
		return -EINVAL;
	}

#if FIXED_PARTITION_EXISTS(storage_partition)
	const struct device *dev = FIXED_PARTITION_DEVICE(storage_partition);
	struct flash_pages_info page_info;
	int rc;

	if (!device_is_ready(dev)) {
		return -ENODEV;
	}

	rc = flash_get_page_info_by_offs(dev, FIXED_PARTITION_OFFSET(storage_partition), &page_info);
	if (rc != 0) {
		return rc;
	}

	if (FIXED_PARTITION_SIZE(storage_partition) < page_info.size) {
		return -ENOSPC;
	}

	*flash_dev = dev;
	*offset = page_info.start_offset;
	*erase_size = page_info.size;
	return 0;
#else
	const struct device *dev = DEVICE_DT_GET(DT_CHOSEN(zephyr_flash_controller));
	const struct flash_parameters *params;
	struct flash_pages_info page_info;
	int rc;

	if (!device_is_ready(dev)) {
		return -ENODEV;
	}

	params = flash_get_parameters(dev);
	if (params == NULL) {
		return -ENODEV;
	}

	rc = flash_get_page_info_by_offs(dev, params->size - 1U, &page_info);
	if (rc != 0) {
		return rc;
	}

	*flash_dev = dev;
	*offset = page_info.start_offset;
	*erase_size = page_info.size;
	return 0;
#endif
}

static int write_flash_record(uint32_t request_id,
			      const struct principal *actor,
			      const uint8_t *data,
			      size_t len,
			      off_t *written_offset)
{
	const struct device *flash_dev;
	const struct flash_parameters *params;
	struct flash_record record;
	uint8_t write_buf[256];
	uint8_t verify_buf[sizeof(record)];
	off_t offset;
	size_t erase_size;
	size_t write_len;
	size_t write_block;
	int rc;

	if ((actor == NULL) || (data == NULL) || (len > FLASH_PAYLOAD_MAX)) {
		return -EINVAL;
	}

	rc = resolve_flash_region(&flash_dev, &offset, &erase_size);
	if (rc != 0) {
		return rc;
	}

	params = flash_get_parameters(flash_dev);
	if (params == NULL) {
		return -ENODEV;
	}

	write_block = MAX((size_t)params->write_block_size, (size_t)1U);
	write_len = ROUND_UP(sizeof(record), write_block);

	if ((write_len > sizeof(write_buf)) || (write_len > erase_size)) {
		return -ENOSPC;
	}

	memset(&record, 0, sizeof(record));
	record.magic = FLASH_RECORD_MAGIC;
	record.request_id = request_id;
	record.uid = actor->uid;
	record.length = (uint32_t)len;
	memcpy(record.payload, data, len);
	record.checksum = simple_checksum(record.payload, sizeof(record.payload));

	memset(write_buf, 0xFF, write_len);
	memcpy(write_buf, &record, sizeof(record));

	rc = flash_erase(flash_dev, offset, erase_size);
	if (rc != 0) {
		return rc;
	}

	rc = flash_write(flash_dev, offset, write_buf, write_len);
	if (rc != 0) {
		return rc;
	}

	rc = flash_read(flash_dev, offset, verify_buf, sizeof(verify_buf));
	if (rc != 0) {
		return rc;
	}

	if (memcmp(verify_buf, &record, sizeof(record)) != 0) {
		return -EIO;
	}

	if (written_offset != NULL) {
		*written_offset = offset;
	}

	return 0;
}

static int apply_config_change(uint32_t key, uint32_t value)
{
	int rc = 0;

	k_mutex_lock(&config_lock, K_FOREVER);

	switch (key) {
	case CONFIG_KEY_MODE:
		system_config.mode = value;
		break;
	case CONFIG_KEY_FLAGS:
		system_config.flags = value;
		break;
	case CONFIG_KEY_SAMPLE_RATE_HZ:
		system_config.sample_rate_hz = value;
		break;
	default:
		rc = -EINVAL;
		break;
	}

	k_mutex_unlock(&config_lock);

	return rc;
}

static void populate_response(struct admin_response *response,
			      uint32_t request_id,
			      int result,
			      const char *fmt,
			      ...)
{
	va_list args;

	response->request_id = request_id;
	response->result = result;

	va_start(args, fmt);
	vsnprintk(response->message, sizeof(response->message), fmt, args);
	va_end(args);
}

static void admin_thread(void *, void *, void *)
{
	struct admin_request request;

	printk("admin: task started (uid=%u perms=0x%x)\n",
	       admin_principal.uid, admin_principal.permissions);

	while (true) {
		struct admin_response response = { 0 };
		struct principal effective;
		int rc;

		k_msgq_get(&admin_request_q, &request, K_FOREVER);

		switch (request.operation) {
		case ADMIN_OP_SET_CONFIG:
			rc = authorize_request(&request.caller, &request.credential,
					       PERM_CONFIG_WRITE, &effective);
			if (rc != 0) {
				populate_response(&response, request.request_id, rc,
						  "config update denied for uid=%u",
						  request.caller.uid);
				break;
			}

			rc = apply_config_change(request.payload.config.key,
						 request.payload.config.value);
			if (rc != 0) {
				populate_response(&response, request.request_id, rc,
						  "invalid config key=%u",
						  request.payload.config.key);
				break;
			}

			populate_response(&response, request.request_id, 0,
					  "config key=%u updated to %u by %s",
					  request.payload.config.key,
					  request.payload.config.value,
					  effective.name);
			break;

		case ADMIN_OP_WRITE_FLASH: {
			off_t flash_offset = 0;

			rc = authorize_request(&request.caller, &request.credential,
					       PERM_FLASH_WRITE, &effective);
			if (rc != 0) {
				populate_response(&response, request.request_id, rc,
						  "flash write denied for uid=%u",
						  request.caller.uid);
				break;
			}

			rc = write_flash_record(request.request_id, &effective,
						request.payload.flash.data,
						request.payload.flash.len,
						&flash_offset);
			if (rc != 0) {
				populate_response(&response, request.request_id, rc,
						  "flash write failed: %d", rc);
				break;
			}

			populate_response(&response, request.request_id, 0,
					  "flash updated at 0x%lx by %s",
					  (unsigned long)flash_offset,
					  effective.name);
			break;
		}

		case ADMIN_OP_SHUTDOWN:
			populate_response(&response, request.request_id, 0,
					  "admin task stopping");
			k_msgq_put(&admin_response_q, &response, K_FOREVER);
			printk("admin: task stopped\n");
			return;

		default:
			populate_response(&response, request.request_id, -EINVAL,
					  "unknown admin operation %d",
					  request.operation);
			break;
		}

		k_msgq_put(&admin_response_q, &response, K_FOREVER);
	}
}

static void wait_for_response(uint32_t request_id)
{
	struct admin_response response;

	while (true) {
		k_msgq_get(&admin_response_q, &response, K_FOREVER);

		if (response.request_id == request_id) {
			printk("user: response[%u] result=%d msg=\"%s\"\n",
			       response.request_id, response.result, response.message);
			return;
		}
	}
}

static uint32_t submit_config_request(const struct principal *caller,
				      uint32_t token,
				      uint32_t key,
				      uint32_t value)
{
	struct admin_request request = { 0 };

	request.request_id = next_request_id++;
	request.caller = *caller;
	request.credential.token = token;
	request.credential.requested_permissions = PERM_CONFIG_WRITE;
	request.operation = ADMIN_OP_SET_CONFIG;
	request.payload.config.key = key;
	request.payload.config.value = value;

	k_msgq_put(&admin_request_q, &request, K_FOREVER);
	return request.request_id;
}

static uint32_t submit_flash_request(const struct principal *caller,
				     uint32_t token,
				     const uint8_t *data,
				     uint32_t len)
{
	struct admin_request request = { 0 };

	request.request_id = next_request_id++;
	request.caller = *caller;
	request.credential.token = token;
	request.credential.requested_permissions = PERM_FLASH_WRITE;
	request.operation = ADMIN_OP_WRITE_FLASH;
	request.payload.flash.len = MIN(len, FLASH_PAYLOAD_MAX);
	memcpy(request.payload.flash.data, data, request.payload.flash.len);

	k_msgq_put(&admin_request_q, &request, K_FOREVER);
	return request.request_id;
}

static uint32_t submit_shutdown_request(const struct principal *caller)
{
	struct admin_request request = { 0 };

	request.request_id = next_request_id++;
	request.caller = *caller;
	request.operation = ADMIN_OP_SHUTDOWN;

	k_msgq_put(&admin_request_q, &request, K_FOREVER);
	return request.request_id;
}

static void print_config_snapshot(void)
{
	struct system_config snapshot;

	k_mutex_lock(&config_lock, K_FOREVER);
	snapshot = system_config;
	k_mutex_unlock(&config_lock);

	printk("config: mode=%u flags=0x%x sample_rate_hz=%u\n",
	       snapshot.mode, snapshot.flags, snapshot.sample_rate_hz);
}

static void user_thread(void *, void *, void *)
{
	static const uint8_t flash_message[] = "user-approved flash write";
	uint32_t request_id;

	k_sleep(K_MSEC(500));

	printk("user: task started (uid=%u perms=0x%x)\n",
	       user_principal.uid, user_principal.permissions);
	print_config_snapshot();

	request_id = submit_config_request(&user_principal, 0U,
					   CONFIG_KEY_MODE, 2U);
	wait_for_response(request_id);

	request_id = submit_config_request(&user_principal, ADMIN_TOKEN,
					   CONFIG_KEY_MODE, 2U);
	wait_for_response(request_id);

	request_id = submit_config_request(&user_principal, ADMIN_TOKEN,
					   CONFIG_KEY_SAMPLE_RATE_HZ, 2000U);
	wait_for_response(request_id);

	request_id = submit_flash_request(&user_principal, ADMIN_TOKEN,
					  flash_message, sizeof(flash_message));
	wait_for_response(request_id);

	print_config_snapshot();

	request_id = submit_shutdown_request(&user_principal);
	wait_for_response(request_id);

	printk("user: task finished\n");
}

K_THREAD_DEFINE(admin_tid, ADMIN_STACK_SIZE, admin_thread,
		NULL, NULL, NULL, ADMIN_PRIORITY, 0, 0);
K_THREAD_DEFINE(user_tid, USER_STACK_SIZE, user_thread,
		NULL, NULL, NULL, USER_PRIORITY, 0, 0);

int main(void)
{
	k_mutex_init(&config_lock);
	printk("privilege demo starting\n");
	return 0;
}