use std::fs::File;
use std::io::Read;
use std::mem::MaybeUninit;
use std::ptr;

pub const CONFIG_BUFFER_SIZE: usize = 4096;

pub unsafe fn read_config_file(path: &str) -> [u8; CONFIG_BUFFER_SIZE] {
    let mut buf = MaybeUninit::<[u8; CONFIG_BUFFER_SIZE]>::uninit();
    let raw: *mut u8 = buf.as_mut_ptr().cast();

    let mut file = match File::open(path) {
        Ok(f) => f,
        Err(_) => {
            ptr::write_bytes(raw, 0, CONFIG_BUFFER_SIZE);
            return buf.assume_init();
        }
    };

    let slice = std::slice::from_raw_parts_mut(raw, CONFIG_BUFFER_SIZE);
    match file.read(slice) {
        Ok(n) => {
            if n < CONFIG_BUFFER_SIZE {
                ptr::write_bytes(raw.add(n), 0, CONFIG_BUFFER_SIZE - n);
            }
        }
        Err(_) => {
            ptr::write_bytes(raw, 0, CONFIG_BUFFER_SIZE);
        }
    }

    buf.assume_init()
}

fn main() {
    let path = std::env::args()
        .nth(1)
        .unwrap_or_else(|| "config.txt".to_string());
    let bytes = unsafe { read_config_file(&path) };
    let _ = bytes;
}
