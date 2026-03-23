#[no_mangle]
pub unsafe extern "C" fn alloc_buffer_from_bytes(data: *const u8, len: usize) -> *mut u8 {
    if len == 0 {
        return ptr::null_mut();
    }