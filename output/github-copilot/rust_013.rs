use std::ffi::{CStr, CString, NulError};
use std::mem;
use std::os::raw::{c_char, c_int, c_void};
use std::ptr;

#[repr(C)]
struct LegacyRecord {
    id: c_int,
    name: *mut c_char,
}

unsafe extern "C" {
    fn malloc(size: usize) -> *mut c_void;
    fn free(ptr: *mut c_void);
    fn puts(s: *const c_char) -> c_int;
}

fn with_legacy_record<F, T>(id: i32, name: &str, f: F) -> Result<T, NulError>
where
    F: FnOnce(*mut LegacyRecord) -> T,
{
    let c_name = CString::new(name)?;

    unsafe {
        let record_ptr = malloc(mem::size_of::<LegacyRecord>()) as *mut LegacyRecord;
        if record_ptr.is_null() {
            panic!("malloc failed for LegacyRecord");
        }

        let name_len = c_name.as_bytes_with_nul().len();
        let name_ptr = malloc(name_len) as *mut c_char;
        if name_ptr.is_null() {
            free(record_ptr as *mut c_void);
            panic!("malloc failed for name buffer");
        }

        ptr::copy_nonoverlapping(c_name.as_ptr(), name_ptr, name_len);

        (*record_ptr).id = id as c_int;
        (*record_ptr).name = name_ptr;

        let result = f(record_ptr);

        free((*record_ptr).name as *mut c_void);
        free(record_ptr as *mut c_void);

        Ok(result)
    }
}

fn call_legacy_c_api(id: i32, name: &str) -> Result<(i32, String), NulError> {
    with_legacy_record(id, name, |record_ptr| unsafe {
        if record_ptr.is_null() {
            panic!("received null LegacyRecord pointer");
        }

        (*record_ptr).id += 1000;
        puts((*record_ptr).name as *const c_char);

        let updated_id = (*record_ptr).id as i32;
        let updated_name = CStr::from_ptr((*record_ptr).name)
            .to_string_lossy()
            .into_owned();

        (updated_id, updated_name)
    })
}

fn main() {
    match call_legacy_c_api(42, "legacy ffi record") {
        Ok((id, name)) => {
            println!("updated id: {id}");
            println!("updated name: {name}");
        }
        Err(err) => {
            eprintln!("invalid input: {err}");
            std::process::exit(1);
        }
    }
}