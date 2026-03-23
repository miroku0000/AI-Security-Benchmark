impl fmt::Display for ConvertError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConvertError::InvalidInput(msg) => write!(f, "invalid input: {msg}"),
            ConvertError::UnsupportedConversion {
                input_ext,
                output_ext,
            } => write!(
                f,
                "unsupported conversion from '{input_ext}' to '{output_ext}'"
            ),
            ConvertError::ToolNotAvailable(tool) => {
                write!(f, "required conversion tool not available: {tool}")
            }
            ConvertError::Io(err) => write!(f, "{err}"),
            ConvertError::CommandFailed { tool, code, stderr } => {
                write!(f, "{tool} failed with status {:?}: {}", code, stderr.trim())
            }
        }
    }
}