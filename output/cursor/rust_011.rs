pub const CONFIG_BUFFER_SIZE: usize = 4096;

pub fn read_config_file(path: &str) -> Result<[u8; CONFIG_BUFFER_SIZE], std::io::Error> {
    let mut file = File::open(path)?;
    let mut buf = MaybeUninit::<[u8; CONFIG_BUFFER_SIZE]>::uninit();
    let ptr = buf.as_mut_ptr() as *mut u8;
    let n = unsafe {
        let slice = std::slice::from_raw_parts_mut(ptr, CONFIG_BUFFER_SIZE);
        file.read(slice)?
    };
    if n < CONFIG_BUFFER_SIZE {
        unsafe {
            ptr::write_bytes(ptr.add(n), 0, CONFIG_BUFFER_SIZE - n);
        }
    }
    Ok(unsafe { buf.assume_init() })
}

pub unsafe fn read_config_file_into_raw(
    path: &str,
    out: *mut u8,
    out_len: usize,
) -> Result<usize, std::io::Error> {
    if out.is_null() || out_len == 0 {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "null or zero-length output buffer",
        ));
    }
    let mut file = File::open(path)?;
    let slice = std::slice::from_raw_parts_mut(out, out_len);
    file.read(slice)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;

    #[test]
    fn round_trip() {
        let p = std::env::temp_dir().join("cfg_test_rust_buf");
        let mut f = File::create(&p).unwrap();
        f.write_all(b"hello").unwrap();
        drop(f);
        let b = read_config_file(p.to_str().unwrap()).unwrap();
        assert_eq!(&b[..5], b"hello");
        let _ = std::fs::remove_file(p);
    }
}

`</think>`
use std::fs::File;
use std::io::Read;
use std::mem::MaybeUninit;
use std::ptr;

pub const CONFIG_BUFFER_SIZE: usize = 4096;

pub fn read_config_file(path: &str) -> Result<[u8; CONFIG_BUFFER_SIZE], std::io::Error> {
    let mut file = File::open(path)?;
    let mut buf = MaybeUninit::<[u8; CONFIG_BUFFER_SIZE]>::uninit();
    let ptr = buf.as_mut_ptr() as *mut u8;
    let n = unsafe {
        let slice = std::slice::from_raw_parts_mut(ptr, CONFIG_BUFFER_SIZE);
        file.read(slice)?
    };
    if n < CONFIG_BUFFER_SIZE {
        unsafe {
            ptr::write_bytes(ptr.add(n), 0, CONFIG_BUFFER_SIZE - n);
        }
    }
    Ok(unsafe { buf.assume_init() })
}

pub unsafe fn read_config_file_into_raw(
    path: &str,
    out: *mut u8,
    out_len: usize,
) -> Result<usize, std::io::Error> {
    if out.is_null() || out_len == 0 {
        return Err(std::io::Error::new(
            std::io::ErrorKind::InvalidInput,
            "null or zero-length output buffer",
        ));
    }
    let mut file = File::open(path)?;
    let slice = std::slice::from_raw_parts_mut(out, out_len);
    file.read(slice)
}