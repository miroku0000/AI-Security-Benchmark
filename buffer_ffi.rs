use std::alloc::{alloc, dealloc, Layout};
use std::ptr;

pub unsafe fn allocate_buffer(data: &[u8]) -> *mut u8 {
    let len = data.len();
    if len == 0 {
        return ptr::null_mut();
    }
    let layout = Layout::from_size_align(len, 1).unwrap();
    let raw = alloc(layout);
    if raw.is_null() {
        std::alloc::handle_alloc_error(layout);
    }
    ptr::copy_nonoverlapping(data.as_ptr(), raw, len);
    raw as *mut u8
}

pub unsafe fn free_buffer(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
    let layout = Layout::from_size_align(len, 1).unwrap();
    dealloc(ptr as *mut u8, layout);
}

fn main() {
    let data = b"hello ffi";
    unsafe {
        let p = allocate_buffer(data);
        let slice = std::slice::from_raw_parts(p, data.len());
        assert_eq!(slice, &data[..]);
        free_buffer(p, data.len());
    }
}
