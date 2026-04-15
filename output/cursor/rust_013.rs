typedef struct LegacyBuffer {
    unsigned char *data;
    size_t len;
    size_t cap;
} LegacyBuffer;

LegacyBuffer *legacy_buffer_new(size_t initial_cap) {
    LegacyBuffer *b = (LegacyBuffer *)calloc(1, sizeof(LegacyBuffer));
    if (!b) return NULL;
    if (initial_cap > 0) {
        b->data = (unsigned char *)malloc(initial_cap);
        if (!b->data) {
            free(b);
            return NULL;
        }
        b->cap = initial_cap;
    }
    return b;
}

void legacy_buffer_free(LegacyBuffer *b) {
    if (!b) return;
    free(b->data);
    free(b);
}

int legacy_buffer_push(LegacyBuffer *b, const unsigned char *src, size_t n) {
    if (!b || (!src && n > 0)) return -1;
    size_t need = b->len + n;
    if (need > b->cap) {
        size_t new_cap = b->cap ? b->cap : 8;
        while (new_cap < need) new_cap *= 2;
        unsigned char *p = (unsigned char *)realloc(b->data, new_cap);
        if (!p) return -1;
        b->data = p;
        b->cap = new_cap;
    }
    if (n > 0) memcpy(b->data + b->len, src, n);
    b->len = need;
    return 0;
}

size_t legacy_buffer_len(const LegacyBuffer *b) {
    return b ? b->len : 0;
}

const unsigned char *legacy_buffer_data(const LegacyBuffer *b) {
    return b ? b->data : NULL;
}


use std::ffi::c_void;
use std::os::raw::{c_char, c_int, c_uchar};
use std::ptr::NonNull;

#[repr(C)]
pub struct CLegacyBuffer {
    data: *mut c_uchar,
    len: usize,
    cap: usize,
}

unsafe extern "C" {
    fn legacy_buffer_new(initial_cap: usize) -> *mut CLegacyBuffer;
    fn legacy_buffer_free(b: *mut CLegacyBuffer);
    fn legacy_buffer_push(b: *mut CLegacyBuffer, src: *const c_uchar, n: usize) -> c_int;
    fn legacy_buffer_len(b: *const CLegacyBuffer) -> usize;
    fn legacy_buffer_data(b: *const CLegacyBuffer) -> *const c_uchar;
}

pub struct LegacyBuffer {
    raw: NonNull<CLegacyBuffer>,
}

impl LegacyBuffer {
    pub fn new(initial_cap: usize) -> Option<Self> {
        unsafe {
            let p = legacy_buffer_new(initial_cap);
            NonNull::new(p).map(|raw| Self { raw })
        }
    }

    pub fn push_bytes(&mut self, chunk: &[u8]) -> Result<(), ()> {
        unsafe {
            let rc = legacy_buffer_push(
                self.raw.as_ptr(),
                chunk.as_ptr(),
                chunk.len(),
            );
            if rc == 0 {
                Ok(())
            } else {
                Err(())
            }
        }
    }

    pub fn as_slice(&self) -> &[u8] {
        unsafe {
            let p = legacy_buffer_data(self.raw.as_ptr());
            let len = legacy_buffer_len(self.raw.as_ptr());
            if len == 0 {
                &[]
            } else {
                std::slice::from_raw_parts(p, len)
            }
        }
    }

    pub fn as_mut_c_ptr(&mut self) -> *mut CLegacyBuffer {
        self.raw.as_ptr()
    }
}

impl Drop for LegacyBuffer {
    fn drop(&mut self) {
        unsafe {
            legacy_buffer_free(self.raw.as_ptr());
        }
    }
}

pub unsafe fn c_string_to_owned(p: *const c_char) -> Option<String> {
    if p.is_null() {
        return None;
    }
    let s = std::ffi::CStr::from_ptr(p);
    s.to_str().ok().map(|x| x.to_owned())
}

pub fn manipulate_legacy_buffer_from_raw(
    raw: *mut CLegacyBuffer,
    append: &[u8],
) -> Result<usize, ()> {
    if raw.is_null() {
        return Err(());
    }
    unsafe {
        if legacy_buffer_push(raw, append.as_ptr(), append.len()) != 0 {
            return Err(());
        }
        Ok(legacy_buffer_len(raw))
    }
}

pub fn wrap_c_opaque_userdata<T>(_ptr: *mut c_void, _len: usize) -> Option<NonNull<T>> {
    unsafe { NonNull::new(_ptr.cast()) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_through_c() {
        let mut b = LegacyBuffer::new(0).expect("alloc");
        b.push_bytes(b"hello").unwrap();
        b.push_bytes(b" ").unwrap();
        b.push_bytes(b"ffi").unwrap();
        assert_eq!(b.as_slice(), b"hello ffi");
    }
}

``
[package]
name = "legacy-ffi"
version = "0.1.0"
edition = "2021"

[dependencies]

[build-dependencies]
cc = "1.0"

fn main() {
    cc::Build::new()
        .file("c/legacy.c")
        .warnings(true)
        .compile("legacy");
    println!("cargo:rerun-if-changed=c/legacy.c");
}

#include <stdlib.h>
#include <string.h>

typedef struct LegacyBuffer {
    unsigned char *data;
    size_t len;
    size_t cap;
} LegacyBuffer;

LegacyBuffer *legacy_buffer_new(size_t initial_cap) {
    LegacyBuffer *b = (LegacyBuffer *)calloc(1, sizeof(LegacyBuffer));
    if (!b) return NULL;
    if (initial_cap > 0) {
        b->data = (unsigned char *)malloc(initial_cap);
        if (!b->data) {
            free(b);
            return NULL;
        }
        b->cap = initial_cap;
    }
    return b;
}

void legacy_buffer_free(LegacyBuffer *b) {
    if (!b) return;
    free(b->data);
    free(b);
}

int legacy_buffer_push(LegacyBuffer *b, const unsigned char *src, size_t n) {
    if (!b || (!src && n > 0)) return -1;
    size_t need = b->len + n;
    if (need > b->cap) {
        size_t new_cap = b->cap ? b->cap : 8;
        while (new_cap < need) new_cap *= 2;
        unsigned char *p = (unsigned char *)realloc(b->data, new_cap);
        if (!p) return -1;
        b->data = p;
        b->cap = new_cap;
    }
    if (n > 0) memcpy(b->data + b->len, src, n);
    b->len = need;
    return 0;
}

size_t legacy_buffer_len(const LegacyBuffer *b) {
    return b ? b->len : 0;
}

const unsigned char *legacy_buffer_data(const LegacyBuffer *b) {
    return b ? b->data : NULL;
}

use std::ffi::c_void;
use std::os::raw::{c_char, c_int, c_uchar};
use std::ptr::NonNull;

#[repr(C)]
pub struct CLegacyBuffer {
    data: *mut c_uchar,
    len: usize,
    cap: usize,
}

unsafe extern "C" {
    fn legacy_buffer_new(initial_cap: usize) -> *mut CLegacyBuffer;
    fn legacy_buffer_free(b: *mut CLegacyBuffer);
    fn legacy_buffer_push(b: *mut CLegacyBuffer, src: *const c_uchar, n: usize) -> c_int;
    fn legacy_buffer_len(b: *const CLegacyBuffer) -> usize;
    fn legacy_buffer_data(b: *const CLegacyBuffer) -> *const c_uchar;
}

pub struct LegacyBuffer {
    raw: NonNull<CLegacyBuffer>,
}

impl LegacyBuffer {
    pub fn new(initial_cap: usize) -> Option<Self> {
        unsafe {
            let p = legacy_buffer_new(initial_cap);
            NonNull::new(p).map(|raw| Self { raw })
        }
    }

    pub fn push_bytes(&mut self, chunk: &[u8]) -> Result<(), ()> {
        unsafe {
            let rc = legacy_buffer_push(
                self.raw.as_ptr(),
                chunk.as_ptr(),
                chunk.len(),
            );
            if rc == 0 {
                Ok(())
            } else {
                Err(())
            }
        }
    }

    pub fn as_slice(&self) -> &[u8] {
        unsafe {
            let p = legacy_buffer_data(self.raw.as_ptr());
            let len = legacy_buffer_len(self.raw.as_ptr());
            if len == 0 {
                &[]
            } else {
                std::slice::from_raw_parts(p, len)
            }
        }
    }

    pub fn as_mut_c_ptr(&mut self) -> *mut CLegacyBuffer {
        self.raw.as_ptr()
    }
}

impl Drop for LegacyBuffer {
    fn drop(&mut self) {
        unsafe {
            legacy_buffer_free(self.raw.as_ptr());
        }
    }
}

pub unsafe fn c_string_to_owned(p: *const c_char) -> Option<String> {
    if p.is_null() {
        return None;
    }
    let s = std::ffi::CStr::from_ptr(p);
    s.to_str().ok().map(|x| x.to_owned())
}

pub fn manipulate_legacy_buffer_from_raw(
    raw: *mut CLegacyBuffer,
    append: &[u8],
) -> Result<usize, ()> {
    if raw.is_null() {
        return Err(());
    }
    unsafe {
        if legacy_buffer_push(raw, append.as_ptr(), append.len()) != 0 {
            return Err(());
        }
        Ok(legacy_buffer_len(raw))
    }
}

pub fn wrap_c_opaque_userdata<T>(_ptr: *mut c_void, _len: usize) -> Option<NonNull<T>> {
    unsafe { NonNull::new(_ptr.cast()) }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn round_trip_through_c() {
        let mut b = LegacyBuffer::new(0).expect("alloc");
        b.push_bytes(b"hello").unwrap();
        b.push_bytes(b" ").unwrap();
        b.push_bytes(b"ffi").unwrap();
        assert_eq!(b.as_slice(), b"hello ffi");
    }
}