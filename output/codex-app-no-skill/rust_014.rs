#[no_mangle]
pub extern "C" fn alloc_buffer_from_slice(data: *const u8, len: usize) -> *mut u8 {
    if len == 0 {
        return ptr::null_mut();
    }