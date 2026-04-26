use std::alloc::{alloc, dealloc, handle_alloc_error, Layout};
use std::ptr::{copy_nonoverlapping, null_mut};

#[unsafe(no_mangle)]
pub unsafe extern "C" fn allocate_buffer(data: *const u8, len: usize) -> *mut u8 {
    if len == 0 {
        return null_mut();
    }

    assert!(!data.is_null(), "data pointer must not be null when len > 0");

    let layout = Layout::array::<u8>(len).expect("invalid layout");
    let ptr = unsafe { alloc(layout) };
    if ptr.is_null() {
        handle_alloc_error(layout);
    }

    unsafe {
        copy_nonoverlapping(data, ptr, len);
    }

    ptr
}

#[unsafe(no_mangle)]
pub unsafe extern "C" fn free_buffer(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }

    let layout = Layout::array::<u8>(len).expect("invalid layout");
    unsafe {
        dealloc(ptr, layout);
    }
}

fn main() {
    let input = b"hello ffi";
    let ptr = unsafe { allocate_buffer(input.as_ptr(), input.len()) };
    assert!(!ptr.is_null());

    let output = unsafe { std::slice::from_raw_parts(ptr, input.len()) };
    println!("{}", std::str::from_utf8(output).unwrap());

    unsafe {
        free_buffer(ptr, input.len());
    }
}