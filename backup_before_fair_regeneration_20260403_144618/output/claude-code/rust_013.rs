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