impl fmt::Display for ConvertError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            ConvertError::EmptyFilename => write!(f, "filename cannot be empty"),
            ConvertError::EmptyFormat => write!(f, "desired format cannot be empty"),
            ConvertError::UnsupportedConversion {
                input_ext,
                output_ext,
            } => write!(
                f,
                "unsupported conversion from '{}' to '{}'",
                input_ext, output_ext
            ),
            ConvertError::MissingFile(path) => write!(f, "input file does not exist: {}", path.display()),
            ConvertError::ToolExecutionFailed { tool, details } => {
                write!(f, "failed to execute '{}': {}", tool, details)
            }
            ConvertError::ToolNotFound(tool) => write!(f, "required conversion tool not found: {}", tool),
            ConvertError::ConversionFailed(details) => write!(f, "conversion failed: {}", details),
        }
    }
}