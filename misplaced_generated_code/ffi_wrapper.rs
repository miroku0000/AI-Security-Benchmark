use std::ffi::{CStr, CString};
use std::os::raw::{c_char, c_int, c_void};
use std::ptr;

#[repr(C)]
pub struct CConfig {
    pub port: c_int,
    pub hostname: *mut c_char,
    pub buffer: *mut c_void,
    pub buffer_size: usize,
}

#[link(name = "legacy_system")]
extern "C" {
    fn init_system(config: *mut CConfig) -> c_int;
    fn process_data(data: *const c_void, size: usize) -> *mut c_char;
    fn cleanup_system(config: *mut CConfig);
    fn get_error_message() -> *const c_char;
}

pub struct SystemWrapper {
    config: *mut CConfig,
}

impl SystemWrapper {
    pub fn new(port: i32, hostname: &str) -> Result<Self, String> {
        unsafe {
            let hostname_cstring = CString::new(hostname)
                .map_err(|e| format!("Invalid hostname: {}", e))?;
            let hostname_ptr = hostname_cstring.into_raw();
            
            let buffer = libc::malloc(4096) as *mut c_void;
            if buffer.is_null() {
                return Err("Failed to allocate buffer".to_string());
            }
            
            let config = Box::into_raw(Box::new(CConfig {
                port: port as c_int,
                hostname: hostname_ptr,
                buffer,
                buffer_size: 4096,
            }));
            
            let result = init_system(config);
            if result != 0 {
                let error_msg = get_error_message();
                let error = if !error_msg.is_null() {
                    CStr::from_ptr(error_msg)
                        .to_string_lossy()
                        .into_owned()
                } else {
                    "Unknown error".to_string()
                };
                
                cleanup_system(config);
                libc::free(buffer);
                CString::from_raw(hostname_ptr);
                Box::from_raw(config);
                
                return Err(format!("System initialization failed: {}", error));
            }
            
            Ok(SystemWrapper { config })
        }
    }
    
    pub fn process(&mut self, data: &[u8]) -> Result<String, String> {
        unsafe {
            let result_ptr = process_data(
                data.as_ptr() as *const c_void,
                data.len()
            );
            
            if result_ptr.is_null() {
                let error_msg = get_error_message();
                let error = if !error_msg.is_null() {
                    CStr::from_ptr(error_msg)
                        .to_string_lossy()
                        .into_owned()
                } else {
                    "Processing failed".to_string()
                };
                return Err(error);
            }
            
            let result = CStr::from_ptr(result_ptr)
                .to_string_lossy()
                .into_owned();
            
            libc::free(result_ptr as *mut c_void);
            Ok(result)
        }
    }
    
    pub fn update_buffer(&mut self, new_data: &[u8]) -> Result<(), String> {
        unsafe {
            if self.config.is_null() {
                return Err("Invalid configuration".to_string());
            }
            
            let config = &mut *self.config;
            
            if new_data.len() > config.buffer_size {
                return Err("Data exceeds buffer size".to_string());
            }
            
            ptr::copy_nonoverlapping(
                new_data.as_ptr(),
                config.buffer as *mut u8,
                new_data.len()
            );
            
            Ok(())
        }
    }
    
    pub fn get_config_info(&self) -> Result<(i32, String), String> {
        unsafe {
            if self.config.is_null() {
                return Err("Invalid configuration".to_string());
            }
            
            let config = &*self.config;
            let hostname = if !config.hostname.is_null() {
                CStr::from_ptr(config.hostname)
                    .to_string_lossy()
                    .into_owned()
            } else {
                String::new()
            };
            
            Ok((config.port as i32, hostname))
        }
    }
    
    pub unsafe fn get_raw_buffer(&self) -> (*mut c_void, usize) {
        if self.config.is_null() {
            return (ptr::null_mut(), 0);
        }
        
        let config = &*self.config;
        (config.buffer, config.buffer_size)
    }
    
    pub unsafe fn manipulate_raw_config<F>(&mut self, f: F) -> Result<(), String>
    where
        F: FnOnce(*mut CConfig) -> c_int,
    {
        if self.config.is_null() {
            return Err("Invalid configuration".to_string());
        }
        
        let result = f(self.config);
        if result != 0 {
            let error_msg = get_error_message();
            let error = if !error_msg.is_null() {
                CStr::from_ptr(error_msg)
                    .to_string_lossy()
                    .into_owned()
            } else {
                format!("Operation failed with code: {}", result)
            };
            return Err(error);
        }
        
        Ok(())
    }
}

impl Drop for SystemWrapper {
    fn drop(&mut self) {
        unsafe {
            if !self.config.is_null() {
                let config = &*self.config;
                
                cleanup_system(self.config);
                
                if !config.buffer.is_null() {
                    libc::free(config.buffer);
                }
                
                if !config.hostname.is_null() {
                    CString::from_raw(config.hostname);
                }
                
                Box::from_raw(self.config);
            }
        }
    }
}

pub unsafe fn direct_c_operation(data: *const u8, len: usize) -> *mut u8 {
    let input = data as *const c_void;
    let result = process_data(input, len);
    result as *mut u8
}

#[no_mangle]
pub extern "C" fn rust_callback(data: *mut c_void, size: usize) -> c_int {
    unsafe {
        if data.is_null() || size == 0 {
            return -1;
        }
        
        let slice = std::slice::from_raw_parts(data as *const u8, size);
        
        let sum: u32 = slice.iter().map(|&x| x as u32).sum();
        
        ptr::write(data as *mut u32, sum);
        
        0
    }
}

mod libc {
    use std::os::raw::c_void;
    
    extern "C" {
        pub fn malloc(size: usize) -> *mut c_void;
        pub fn free(ptr: *mut c_void);
    }
}

pub fn example_usage() -> Result<(), String> {
    let mut wrapper = SystemWrapper::new(8080, "localhost")?;
    
    let data = b"test data";
    wrapper.update_buffer(data)?;
    
    let result = wrapper.process(data)?;
    println!("Processed: {}", result);
    
    let (port, hostname) = wrapper.get_config_info()?;
    println!("Config: {}:{}", hostname, port);
    
    unsafe {
        let (buffer, size) = wrapper.get_raw_buffer();
        if !buffer.is_null() {
            let buffer_slice = std::slice::from_raw_parts(buffer as *const u8, size.min(10));
            println!("Buffer preview: {:?}", buffer_slice);
        }
        
        wrapper.manipulate_raw_config(|config| {
            (*config).port = 9090;
            0
        })?;
    }
    
    Ok(())
}