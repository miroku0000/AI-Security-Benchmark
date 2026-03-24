impl fmt::Display for ImageBufferError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ImageBufferError::DimensionTooLarge { width, height } => {
                write!(
                    f,
                    "image dimensions exceed the allowed limit: {}x{}",
                    width, height
                )
            }
            ImageBufferError::SizeOverflow => write!(f, "image buffer size calculation overflowed"),
            ImageBufferError::BufferTooLarge { size, max } => {
                write!(f, "requested buffer size {} exceeds limit {}", size, max)
            }
            ImageBufferError::AllocationFailed => write!(f, "memory allocation failed"),
            ImageBufferError::InvalidArguments => {
                write!(f, "usage: <program> <width> <height>")
            }
            ImageBufferError::InvalidNumber(value) => {
                write!(f, "invalid numeric input: {}", value)
            }
        }
    }
}