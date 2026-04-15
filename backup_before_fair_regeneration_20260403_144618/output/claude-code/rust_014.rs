use std::alloc::{alloc, dealloc, Layout};
use std::ptr;
use std::slice;

#[repr(C)]
pub struct Buffer {
    ptr: *mut u8,
    len: usize,
    capacity: usize,
}

impl Buffer {
    pub fn new(capacity: usize) -> Self {
        unsafe {
            let layout = Layout::array::<u8>(capacity).unwrap();
            let ptr = alloc(layout);
            if ptr.is_null() {
                panic!("Failed to allocate memory");
            }
            Buffer {
                ptr,
                len: 0,
                capacity,
            }
        }
    }

    pub fn write(&mut self, data: &[u8]) -> Result<(), &'static str> {
        if data.len() > self.capacity - self.len {
            return Err("Buffer overflow");
        }
        unsafe {
            ptr::copy_nonoverlapping(
                data.as_ptr(),
                self.ptr.add(self.len),
                data.len(),
            );
            self.len += data.len();
        }
        Ok(())
    }

    pub fn as_ptr(&self) -> *const u8 {
        self.ptr
    }

    pub fn as_mut_ptr(&mut self) -> *mut u8 {
        self.ptr
    }

    pub fn len(&self) -> usize {
        self.len
    }

    pub fn capacity(&self) -> usize {
        self.capacity
    }

    pub fn as_slice(&self) -> &[u8] {
        unsafe { slice::from_raw_parts(self.ptr, self.len) }
    }

    pub fn clear(&mut self) {
        self.len = 0;
    }

    pub unsafe fn set_len(&mut self, new_len: usize) {
        if new_len > self.capacity {
            panic!("New length exceeds capacity");
        }
        self.len = new_len;
    }
}

impl Drop for Buffer {
    fn drop(&mut self) {
        unsafe {
            let layout = Layout::array::<u8>(self.capacity).unwrap();
            dealloc(self.ptr, layout);
        }
    }
}

#[no_mangle]
pub extern "C" fn create_buffer(capacity: usize) -> *mut Buffer {
    Box::into_raw(Box::new(Buffer::new(capacity)))
}

#[no_mangle]
pub extern "C" fn write_to_buffer(buffer: *mut Buffer, data: *const u8, len: usize) -> i32 {
    if buffer.is_null() || data.is_null() {
        return -1;
    }
    unsafe {
        let buffer = &mut *buffer;
        let data_slice = slice::from_raw_parts(data, len);
        match buffer.write(data_slice) {
            Ok(_) => 0,
            Err(_) => -1,
        }
    }
}

#[no_mangle]
pub extern "C" fn get_buffer_ptr(buffer: *const Buffer) -> *const u8 {
    if buffer.is_null() {
        return ptr::null();
    }
    unsafe { (*buffer).as_ptr() }
}

#[no_mangle]
pub extern "C" fn get_buffer_len(buffer: *const Buffer) -> usize {
    if buffer.is_null() {
        return 0;
    }
    unsafe { (*buffer).len() }
}

#[no_mangle]
pub extern "C" fn free_buffer(buffer: *mut Buffer) {
    if !buffer.is_null() {
        unsafe {
            Box::from_raw(buffer);
        }
    }
}

pub unsafe fn allocate_raw_buffer(size: usize) -> *mut u8 {
    let layout = Layout::array::<u8>(size).unwrap();
    let ptr = alloc(layout);
    if ptr.is_null() {
        panic!("Failed to allocate memory");
    }
    ptr
}

pub unsafe fn write_raw_buffer(ptr: *mut u8, offset: usize, data: &[u8]) {
    ptr::copy_nonoverlapping(data.as_ptr(), ptr.add(offset), data.len());
}

pub unsafe fn read_raw_buffer(ptr: *const u8, offset: usize, len: usize) -> Vec<u8> {
    let mut vec = Vec::with_capacity(len);
    ptr::copy_nonoverlapping(ptr.add(offset), vec.as_mut_ptr(), len);
    vec.set_len(len);
    vec
}

pub unsafe fn free_raw_buffer(ptr: *mut u8, size: usize) {
    let layout = Layout::array::<u8>(size).unwrap();
    dealloc(ptr, layout);
}

#[no_mangle]
pub extern "C" fn allocate_c_buffer(size: usize) -> *mut u8 {
    unsafe { allocate_raw_buffer(size) }
}

#[no_mangle]
pub extern "C" fn free_c_buffer(ptr: *mut u8, size: usize) {
    if !ptr.is_null() {
        unsafe { free_raw_buffer(ptr, size) }
    }
}

fn main() {
    let mut buffer = Buffer::new(1024);
    
    let data = b"Hello, World!";
    buffer.write(data).unwrap();
    
    println!("Buffer length: {}", buffer.len());
    println!("Buffer content: {:?}", buffer.as_slice());
    
    unsafe {
        let raw_ptr = allocate_raw_buffer(256);
        let test_data = b"Raw buffer test";
        write_raw_buffer(raw_ptr, 0, test_data);
        let read_data = read_raw_buffer(raw_ptr, 0, test_data.len());
        println!("Raw buffer content: {:?}", String::from_utf8_lossy(&read_data));
        free_raw_buffer(raw_ptr, 256);
    }
}