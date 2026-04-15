impl fmt::Display for CacheError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CacheError::Io(err) => write!(f, "io error: {err}"),
            CacheError::Encode(err) => write!(f, "serialization error: {err}"),
            CacheError::Decode(err) => write!(f, "deserialization error: {err}"),
            CacheError::InvalidBaseDir => write!(f, "invalid base directory"),
            CacheError::InvalidCachePath => write!(f, "invalid cache path"),
            CacheError::FileTooLarge(size) => {
                write!(f, "cache file too large: {size} bytes")
            }
            CacheError::CacheVersionMismatch { expected, found } => {
                write!(f, "cache version mismatch: expected {expected}, found {found}")
            }
            CacheError::MissingCache => write!(f, "cache file does not exist"),
        }
    }
}