impl fmt::Display for PacketError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            PacketError::Truncated => write!(f, "packet is truncated"),
            PacketError::InvalidVersion(v) => write!(f, "invalid packet version: {}", v),
            PacketError::PayloadTooLarge(len) => write!(f, "payload too large: {}", len),
            PacketError::LengthMismatch { declared, actual } => {
                write!(f, "payload length mismatch: declared={}, actual={}", declared, actual)
            }
            PacketError::ChecksumMismatch { expected, actual } => {
                write!(f, "checksum mismatch: expected={}, actual={}", expected, actual)
            }
        }
    }
}