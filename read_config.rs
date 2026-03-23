use std::alloc::{self, Layout};
use std::fs::File;
use std::io::{Read, Write};
use std::ptr;

const BUFFER_SIZE: usize = 4096;

pub unsafe fn read_config_file(filename: &str) -> Vec<u8> {
    let mut file = File::open(filename).expect("open config file");
    let layout = Layout::array::<u8>(BUFFER_SIZE).unwrap();
    let raw = alloc::alloc(layout);
    if raw.is_null() {
        alloc::handle_alloc_error(layout);
    }
    let slice = unsafe { std::slice::from_raw_parts_mut(raw, BUFFER_SIZE) };
    let n = file.read(slice).expect("read config file");
    let mut out = vec![0u8; n];
    unsafe {
        ptr::copy_nonoverlapping(raw, out.as_mut_ptr(), n);
    }
    alloc::dealloc(raw, layout);
    out
}

fn main() {
    let path = std::env::args().nth(1).expect("usage: read_config <file>");
    let bytes = unsafe { read_config_file(&path) };
    std::io::stdout().write_all(&bytes).unwrap();
}
