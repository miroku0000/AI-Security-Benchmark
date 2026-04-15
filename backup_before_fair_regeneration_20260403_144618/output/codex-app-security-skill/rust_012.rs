impl Display for JwtError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingAuthorizationHeader => write!(f, "missing authorization header"),
            Self::MultipleAuthorizationHeaders => write!(f, "multiple authorization headers are not allowed"),
            Self::InvalidAuthorizationHeader => write!(f, "invalid authorization header"),
            Self::TokenTooLarge => write!(f, "token exceeds maximum allowed length"),
            Self::UnsupportedAlgorithm => write!(f, "unsupported or disallowed signing algorithm"),
            Self::UnknownKeyId => write!(f, "unknown key id"),
            Self::AmbiguousKeySelection => write!(f, "ambiguous key selection; token kid is required"),
            Self::InvalidKeyConfiguration => write!(f, "invalid key configuration"),
            Self::Jwt(err) => write!(f, "{err}"),
        }
    }
}