unsafe extern "C" {
    fn legacy_record_create(name: *const c_char, value: c_int) -> *mut LegacyRecord;
    fn legacy_record_set_value(record: *mut LegacyRecord, value: c_int);
    fn legacy_record_get_value(record: *const LegacyRecord) -> c_int;
    fn legacy_record_get_name(record: *const LegacyRecord) -> *const c_char;
    fn legacy_record_destroy(record: *mut LegacyRecord);
}