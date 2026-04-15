static uint32_t config_record_crc(const struct persisted_config_record *record)
{
	return crc32_ieee((const uint8_t *)record, offsetof(struct persisted_config_record, crc32));
}