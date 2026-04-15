static int admin_modify_system_config(const struct credential *cred,
				      const struct system_config *new_cfg)
{
	if (!has_capability(cred, CAP_CONFIG_MODIFY)) {
		return STATUS_DENIED;
	}