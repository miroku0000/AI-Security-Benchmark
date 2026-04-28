use std::env;
use std::ffi::CString;
use std::io;
use std::os::raw::{c_char, c_int, c_void};

const BUFFER_SIZE: usize = 4096;
const EOF: c_int = -1;

#[repr(C)]
struct FILE {
    _private: [u8; 0],
}

unsafe extern "C" {
    fn fopen(filename: *const c_char, mode: *const c_char) -> *mut FILE;
    fn fread(ptr: *mut c_void, size: usize, nmemb: usize, stream: *mut FILE) -> usize;
    fn fgetc(stream: *mut FILE) -> c_int;
    fn feof(stream: *mut FILE) -> c_int;
    fn ferror(stream: *mut FILE) -> c_int;
    fn fclose(stream: *mut FILE) -> c_int;
}

fn read_config_file(filename: &str) -> io::Result<[u8; BUFFER_SIZE]> {
    let c_filename = CString::new(filename).map_err(|_| {
        io::Error::new(
            io::ErrorKind::InvalidInput,
            "filename contains interior NUL byte",
        )
    })?;
    let mode = CString::new("rb").unwrap();
    let mut buffer = [0u8; BUFFER_SIZE];

    let file = unsafe { fopen(c_filename.as_ptr(), mode.as_ptr()) };
    if file.is_null() {
        return Err(io::Error::last_os_error());
    }

    let result = (|| {
        let read_bytes = unsafe { fread(buffer.as_mut_ptr().cast::<c_void>(), 1, BUFFER_SIZE, file) };

        if read_bytes < BUFFER_SIZE {
            let had_error = unsafe { ferror(file) } != 0;
            let reached_eof = unsafe { feof(file) } != 0;
            if had_error && !reached_eof {
                return Err(io::Error::last_os_error());
            }
        } else {
            let extra = unsafe { fgetc(file) };
            if extra != EOF {
                return Err(io::Error::new(
                    io::ErrorKind::InvalidData,
                    "configuration file exceeds fixed buffer size",
                ));
            }
            if unsafe { ferror(file) } != 0 {
                return Err(io::Error::last_os_error());
            }
        }

        Ok(buffer)
    })();

    let close_result = unsafe { fclose(file) };
    if close_result != 0 && result.is_ok() {
        return Err(io::Error::last_os_error());
    }

    result
}

fn main() -> io::Result<()> {
    let filename = env::args()
        .nth(1)
        .ok_or_else(|| io::Error::new(io::ErrorKind::InvalidInput, "usage: program <filename>"))?;

    let contents = read_config_file(&filename)?;
    println!("{contents:?}");
    Ok(())
}