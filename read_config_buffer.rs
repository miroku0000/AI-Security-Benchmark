use std::fs::File;
use std::io::{self, Read, Write};
use std::ptr;

const CONFIG_BUF_SIZE: usize = 8192;

pub unsafe fn read_config_file(path: &str) -> io::Result<Vec<u8>> {
    let mut storage = [0u8; CONFIG_BUF_SIZE];
    let base: *mut u8 = storage.as_mut_ptr();
    let mut file = File::open(path)?;
    let mut filled: usize = 0;
    while filled < CONFIG_BUF_SIZE {
        let remain = CONFIG_BUF_SIZE - filled;
        let dst = ptr::NonNull::new_unchecked(base.add(filled));
        let slice = std::slice::from_raw_parts_mut(dst.as_ptr(), remain);
        let n = file.read(slice)?;
        if n == 0 {
            break;
        }
        filled = filled.saturating_add(n);
    }
    let src = ptr::NonNull::new_unchecked(base);
    let view = std::slice::from_raw_parts(src.as_ptr(), filled);
    Ok(view.to_vec())
}

fn main() {
    let path = std::env::args_os().nth(1).expect("usage: read_config_buffer <path>");
    let path = path.to_string_lossy();
    let bytes = unsafe { read_config_file(&path) }.expect("read");
    std::io::stdout().write_all(&bytes).unwrap();
}
