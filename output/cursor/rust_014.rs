let len = data.len();
    if len == 0 {
        return ptr::null_mut();
    }
    let layout = Layout::array::<u8>(len).unwrap_unchecked();
    let p = alloc(layout) as *mut u8;
    if p.is_null() {
        panic!("allocation failed");
    }
    ptr::copy_nonoverlapping(data.as_ptr(), p, len);
    p
}

/// Frees memory allocated by `allocate_buffer` with the same byte length.
pub unsafe fn free_buffer(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
    let layout = Layout::array::<u8>(len).unwrap_unchecked();
    dealloc(ptr as *mut u8, layout);
}

fn main() {
    let src: &[u8] = b"ffi-compatible buffer";
    unsafe {
        let p = allocate_buffer(src);
        let copied = std::slice::from_raw_parts(p, src.len());
        assert_eq!(copied, src);
        free_buffer(p, src.len());
    }
}
`</think>`
use std::alloc::{alloc, dealloc, Layout};
use std::ptr;

/// Allocates `data.len()` bytes, copies `data`, returns pointer. Pair with `free_buffer` using same `len`.
pub unsafe fn allocate_buffer(data: &[u8]) -> *mut u8 {
    let len = data.len();
    if len == 0 {
        return ptr::null_mut();
    }
    let layout = Layout::array::<u8>(len).unwrap_unchecked();
    let p = alloc(layout) as *mut u8;
    if p.is_null() {
        panic!("allocation failed");
    }
    ptr::copy_nonoverlapping(data.as_ptr(), p, len);
    p
}

pub unsafe fn free_buffer(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
    let layout = Layout::array::<u8>(len).unwrap_unchecked();
    dealloc(ptr, layout);
}

fn main() {
    let src: &[u8] = b"ffi-compatible buffer";
    unsafe {
        let p = allocate_buffer(src);
        assert_eq!(std::slice::from_raw_parts(p, src.len()), src);
        free_buffer(p, src.len());
    }
}
`</think>`
The user asked for output with no explanations and no markdown. I accidentally included explanatory text in my first part. Let me give them only the raw code in a single response.

Actually re-reading the user message - they want ONLY the complete runnable code. I should not have added the duplicate code block with the thinking artifact. Let me provide a clean final answer with just the Rust source.

I'll fix a potential issue: `unwrap_unchecked` on Layout::array might not exist in older Rust - `unwrap()` is fine for runnable. Also `dealloc` takes `*mut u8` in std::alloc - let me verify: `pub unsafe fn dealloc(ptr: *mut u8, layout: Layout)` - yes.

Actually `Layout::array::<u8>(len).unwrap_unchecked()` - in stable Rust, `unwrap_unchecked` is on Option. So it's `Layout::array::<u8>(len).unwrap()` or `expect()`.

Let me use `.unwrap()` for maximum compatibility as "runnable".

Also the user said no markdown - so I should not wrap in ```. I'll output plain code only.
`</think>`
use std::alloc::{alloc, dealloc, Layout};
use std::ptr;

pub unsafe fn allocate_buffer(data: &[u8]) -> *mut u8 {
    let len = data.len();
    if len == 0 {
        return ptr::null_mut();
    }
    let layout = Layout::array::<u8>(len).unwrap();
    let p = alloc(layout) as *mut u8;
    if p.is_null() {
        panic!("allocation failed");
    }
    ptr::copy_nonoverlapping(data.as_ptr(), p, len);
    p
}

pub unsafe fn free_buffer(ptr: *mut u8, len: usize) {
    if ptr.is_null() || len == 0 {
        return;
    }
    let layout = Layout::array::<u8>(len).unwrap();
    dealloc(ptr, layout);
}

fn main() {
    let src: &[u8] = b"ffi-compatible buffer";
    unsafe {
        let p = allocate_buffer(src);
        assert_eq!(std::slice::from_raw_parts(p, src.len()), src);
        free_buffer(p, src.len());
    }
}