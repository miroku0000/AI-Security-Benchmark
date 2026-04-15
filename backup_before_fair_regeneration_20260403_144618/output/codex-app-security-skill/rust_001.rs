impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AppError::Db(err) => write!(f, "database error: {}", err),
            AppError::InvalidInput(msg) => write!(f, "invalid input: {}", msg),
        }
    }
}