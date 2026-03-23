impl fmt::Display for AuthError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            AuthError::MissingAuthorizationHeader => write!(f, "missing Authorization header"),
            AuthError::InvalidAuthorizationHeader => write!(f, "invalid Authorization header"),
            AuthError::InvalidTokenHeader(err) => write!(f, "invalid token header: {err}"),
            AuthError::UnsupportedAlgorithm(alg) => write!(f, "unsupported JWT algorithm: {alg:?}"),
            AuthError::NoMatchingVerifier => write!(f, "no matching verifier found for token"),
            AuthError::VerificationFailed(err) => write!(f, "token verification failed: {err}"),
        }
    }
}