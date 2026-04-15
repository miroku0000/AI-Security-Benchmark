unsafe extern "C" {
    fn legacy_record_new() -> *mut CLegacyRecord;
    fn legacy_record_free(record: *mut CLegacyRecord);
    fn legacy_record_set_name(
        record: *mut CLegacyRecord,
        name: *const c_char,
        name_len: usize,
    ) -> c_int;
    fn legacy_record_get_name(record: *const CLegacyRecord, out_len: *mut usize) -> *const c_char;
}