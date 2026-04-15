typedef uint32_t cap_mask_t;

#define CAP_NONE           0U
#define CAP_READ_CONFIG    (1U << 0)
#define CAP_WRITE_CONFIG   (1U << 1)
#define CAP_FLASH_WRITE    (1U << 2)

typedef enum {
	OP_READ_CONFIG = 1,
	OP_WRITE_CONFIG,
	OP_FLASH_ERASE_PROGRAM,
} admin_op_t;

typedef enum {
	SUBJECT_USER = 1000,
	SUBJECT_ROOT = 0,
} subject_uid_t;

struct system_config {
	uint32_t magic;
	uint32_t feature_flags;
	uint32_t telemetry_interval_ms;
	char     hostname[32];
};

struct admin_request {
	admin_op_t op;
	subject_uid_t uid;
	cap_mask_t presented_caps;
	union {
		struct {
			struct system_config cfg;
		} config;
		struct {
			uint32_t offset;
			uint8_t data[64];
			size_t len;
		} flash;
	} u;
	int result;
	struct k_sem *done;
};

K_MSGQ_DEFINE(admin_msgq, sizeof(struct admin_request *), 8,
	      sizeof(struct admin_request *));

static struct system_config g_sys_config;
static uint8_t g_flash[FLASH_SIM_SIZE];
static K_THREAD_STACK_DEFINE(admin_stack, 2048);
static K_THREAD_STACK_DEFINE(user_stack, 2048);
static struct k_thread admin_thr;
static struct k_thread user_thr;
static k_tid_t admin_tid;

static cap_mask_t effective_caps_for_uid(subject_uid_t uid)
{
	if (uid == SUBJECT_ROOT) {
		return CAP_READ_CONFIG | CAP_WRITE_CONFIG | CAP_FLASH_WRITE;
	}
	return CAP_READ_CONFIG;
}

static cap_mask_t required_caps_for_op(admin_op_t op)
{
	switch (op) {
	case OP_READ_CONFIG:
		return CAP_READ_CONFIG;
	case OP_WRITE_CONFIG:
		return CAP_WRITE_CONFIG;
	case OP_FLASH_ERASE_PROGRAM:
		return CAP_FLASH_WRITE;
	default:
		return CAP_NONE;
	}
}

static bool has_all_caps(cap_mask_t have, cap_mask_t need)
{
	return (have & need) == need;
}

static int privilege_check(const struct admin_request *req)
{
	cap_mask_t eff = effective_caps_for_uid(req->uid);
	cap_mask_t need = required_caps_for_op(req->op);

	if (!has_all_caps(eff, need)) {
		return -EPERM;
	}
	if (!has_all_caps(req->presented_caps, need)) {
		return -EACCES;
	}
	return 0;
}

static int do_read_config(struct admin_request *req)
{
	memcpy(&req->u.config.cfg, &g_sys_config, sizeof(g_sys_config));
	return 0;
}

static int do_write_config(struct admin_request *req)
{
	if (req->u.config.cfg.magic != CONFIG_MAGIC) {
		return -EINVAL;
	}
	memcpy(&g_sys_config, &req->u.config.cfg, sizeof(g_sys_config));
	return 0;
}

static int flash_sector_erase(uint32_t offset)
{
	uint32_t base = offset - (offset % FLASH_SECTOR_SIZE);

	if (base >= FLASH_SIM_SIZE) {
		return -EINVAL;
	}
	memset(&g_flash[base], 0xFF, FLASH_SECTOR_SIZE);
	return 0;
}

static int flash_program(uint32_t offset, const uint8_t *data, size_t len)
{
	size_t i;

	if (!data || len > sizeof(((struct admin_request *)0)->u.flash.data)) {
		return -EINVAL;
	}
	if (offset >= FLASH_SIM_SIZE || len > FLASH_SIM_SIZE - offset) {
		return -EINVAL;
	}
	for (i = 0; i < len; i++) {
		uint8_t cur = g_flash[offset + i];
		uint8_t w = data[i];

		if ((uint8_t)(cur & w) != w) {
			return -EIO;
		}
		g_flash[offset + i] = cur & w;
	}
	return 0;
}

static int do_flash_erase_program(struct admin_request *req)
{
	int err;

	err = flash_sector_erase(req->u.flash.offset);
	if (err != 0) {
		return err;
	}
	return flash_program(req->u.flash.offset, req->u.flash.data, req->u.flash.len);
}

static void admin_dispatch(struct admin_request *req)
{
	int err = privilege_check(req);

	if (err != 0) {
		req->result = err;
		return;
	}
	if (k_current_get() != admin_tid) {
		req->result = -EPERM;
		return;
	}

	switch (req->op) {
	case OP_READ_CONFIG:
		req->result = do_read_config(req);
		break;
	case OP_WRITE_CONFIG:
		req->result = do_write_config(req);
		break;
	case OP_FLASH_ERASE_PROGRAM:
		req->result = do_flash_erase_program(req);
		break;
	default:
		req->result = -ENOTSUP;
		break;
	}
}

static int rpc_admin_op(struct admin_request *req, k_timeout_t timeout)
{
	int err;
	struct admin_request *p = req;

	err = k_msgq_put(&admin_msgq, &p, timeout);
	if (err != 0) {
		return err;
	}
	err = k_sem_take(req->done, timeout);
	if (err != 0) {
		return err;
	}
	return req->result;
}

static void admin_task(void *a, void *b, void *c)
{
	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(c);

	admin_tid = k_current_get();

	for (;;) {
		struct admin_request *req;
		int got = k_msgq_get(&admin_msgq, &req, K_FOREVER);

		if (got != 0) {
			continue;
		}
		admin_dispatch(req);
		if (req->done) {
			k_sem_give(req->done);
		}
	}
}

static cap_mask_t delegate_caps_for_user(subject_uid_t uid, admin_op_t op)
{
	cap_mask_t base = effective_caps_for_uid(uid);
	cap_mask_t need = required_caps_for_op(op);

	return base & need;
}

static void user_task(void *a, void *b, void *c)
{
	ARG_UNUSED(a);
	ARG_UNUSED(b);
	ARG_UNUSED(c);

	struct k_sem done;
	struct admin_request req;
	int err;

	k_sem_init(&done, 0, 1);

	memset(&req, 0, sizeof(req));
	req.op = OP_READ_CONFIG;
	req.uid = SUBJECT_USER;
	req.presented_caps = delegate_caps_for_user(SUBJECT_USER, OP_READ_CONFIG);
	req.done = &done;
	err = rpc_admin_op(&req, K_MSEC(500));
	printk("user read config: %d flags=%u\n", err,
	       err == 0 ? req.u.config.cfg.feature_flags : 0U);

	memset(&req, 0, sizeof(req));
	req.op = OP_WRITE_CONFIG;
	req.uid = SUBJECT_USER;
	req.presented_caps = delegate_caps_for_user(SUBJECT_USER, OP_WRITE_CONFIG);
	req.u.config.cfg = g_sys_config;
	req.u.config.cfg.feature_flags ^= 1U;
	req.done = &done;
	err = rpc_admin_op(&req, K_MSEC(500));
	printk("user write config (expect deny): %d\n", err);

	memset(&req, 0, sizeof(req));
	req.op = OP_FLASH_ERASE_PROGRAM;
	req.uid = SUBJECT_USER;
	req.presented_caps =
		CAP_FLASH_WRITE & delegate_caps_for_user(SUBJECT_USER, OP_FLASH_ERASE_PROGRAM);
	req.u.flash.offset = 0;
	req.u.flash.data[0] = 0xAB;
	req.u.flash.len = 1;
	req.done = &done;
	err = rpc_admin_op(&req, K_MSEC(500));
	printk("user flash write (expect deny): %d\n", err);

	memset(&req, 0, sizeof(req));
	req.op = OP_WRITE_CONFIG;
	req.uid = SUBJECT_ROOT;
	req.presented_caps = CAP_WRITE_CONFIG;
	req.u.config.cfg = g_sys_config;
	req.u.config.cfg.telemetry_interval_ms = 250;
	strncpy(req.u.config.cfg.hostname, "device", sizeof(req.u.config.cfg.hostname) - 1);
	req.done = &done;
	err = rpc_admin_op(&req, K_MSEC(500));
	printk("root write config via IPC: %d interval=%u\n", err,
	       err == 0 ? g_sys_config.telemetry_interval_ms : 0U);

	memset(&req, 0, sizeof(req));
	req.op = OP_READ_CONFIG;
	req.uid = SUBJECT_ROOT;
	req.presented_caps = CAP_READ_CONFIG;
	req.done = &done;
	err = rpc_admin_op(&req, K_MSEC(500));
	if (err == 0) {
		printk("root read: host=%s\n", req.u.config.cfg.hostname);
	}

	memset(&req, 0, sizeof(req));
	req.op = OP_FLASH_ERASE_PROGRAM;
	req.uid = SUBJECT_ROOT;
	req.presented_caps = CAP_FLASH_WRITE;
	req.u.flash.offset = 0;
	req.u.flash.data[0] = 0x5A;
	req.u.flash.len = 1;
	req.done = &done;
	err = rpc_admin_op(&req, K_MSEC(500));
	printk("root flash program: %d flash[0]=0x%02x\n", err,
	       err == 0 ? g_flash[0] : 0U);
}

int main(void)
{
	memset(&g_sys_config, 0, sizeof(g_sys_config));
	g_sys_config.magic = CONFIG_MAGIC;
	g_sys_config.feature_flags = 0x3U;
	g_sys_config.telemetry_interval_ms = 1000;
	strncpy(g_sys_config.hostname, "zephyr-node", sizeof(g_sys_config.hostname) - 1);
	memset(g_flash, 0xFF, sizeof(g_flash));

	k_thread_create(&admin_thr, admin_stack, K_THREAD_STACK_SIZEOF(admin_stack),
			admin_task, NULL, NULL, NULL, K_PRIO_COOP(2), 0, K_NO_WAIT);
	k_thread_name_set(&admin_thr, "admin");
	k_thread_create(&user_thr, user_stack, K_THREAD_STACK_SIZEOF(user_stack),
			user_task, NULL, NULL, NULL, K_PRIO_PREEMPT(5), 0, K_NO_WAIT);
	k_thread_name_set(&user_thr, "user");
	return 0;
}