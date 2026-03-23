impl FfiBuffer {
    pub const fn null() -> Self {
        Self {
            ptr: ptr::null_mut(),
            len: 0,
        }
    }
}