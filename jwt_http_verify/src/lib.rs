use std::collections::HashSet;

use http::header::AUTHORIZATION;
use http::HeaderMap;
use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserClaims {
    pub sub: String,
    #[serde(default)]
    pub email: Option<String>,
    #[serde(default)]
    pub name: Option<String>,
}

#[derive(Debug, Clone)]
pub struct UserInfo {
    pub user_id: String,
    pub email: Option<String>,
    pub name: Option<String>,
    pub claims: UserClaims,
}

#[derive(Debug)]
pub enum JwtError {
    MissingAuthHeader,
    InvalidBearer,
    MissingKey,
    UnsupportedAlgorithm(Algorithm),
    Jwt(jsonwebtoken::errors::Error),
}

impl std::fmt::Display for JwtError {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        match self {
            JwtError::MissingAuthHeader => write!(f, "missing Authorization header"),
            JwtError::InvalidBearer => write!(f, "invalid Bearer token"),
            JwtError::MissingKey => write!(f, "no decoding key configured for algorithm"),
            JwtError::UnsupportedAlgorithm(a) => write!(f, "unsupported algorithm: {a:?}"),
            JwtError::Jwt(e) => write!(f, "{e}"),
        }
    }
}

impl std::error::Error for JwtError {}

impl From<jsonwebtoken::errors::Error> for JwtError {
    fn from(e: jsonwebtoken::errors::Error) -> Self {
        JwtError::Jwt(e)
    }
}

pub fn bearer_token(headers: &HeaderMap) -> Result<&str, JwtError> {
    let raw = headers
        .get(AUTHORIZATION)
        .ok_or(JwtError::MissingAuthHeader)?
        .to_str()
        .map_err(|_| JwtError::InvalidBearer)?;
    let token = raw
        .strip_prefix("Bearer ")
        .or_else(|| raw.strip_prefix("bearer "))
        .ok_or(JwtError::InvalidBearer)?;
    if token.is_empty() {
        return Err(JwtError::InvalidBearer);
    }
    Ok(token)
}

pub struct JwtVerifier<'a> {
    pub hs256_secrets: &'a [&'a [u8]],
    pub rsa_public_pems: &'a [&'a [u8]],
    pub ecdsa_public_pems: &'a [&'a [u8]],
}

impl<'a> JwtVerifier<'a> {
    pub fn verify_request(&self, headers: &HeaderMap) -> Result<UserInfo, JwtError> {
        let token = bearer_token(headers)?;
        self.verify_token(token)
    }

    pub fn verify_token(&self, token: &str) -> Result<UserInfo, JwtError> {
        let header = decode_header(token)?;
        let alg = header.alg;
        if !allowed_algorithms().contains(&alg) {
            return Err(JwtError::UnsupportedAlgorithm(alg));
        }
        let mut validation = Validation::new(alg);
        validation.algorithms = allowed_algorithms();
        let key = self.decoding_key_for_algorithm(alg)?;
        let token_data = decode::<UserClaims>(token, &key, &validation)?;
        let claims = token_data.claims;
        Ok(UserInfo {
            user_id: claims.sub.clone(),
            email: claims.email.clone(),
            name: claims.name.clone(),
            claims,
        })
    }

    fn decoding_key_for_algorithm(&self, alg: Algorithm) -> Result<DecodingKey, JwtError> {
        match alg {
            Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512 => self
                .hs256_secrets
                .first()
                .map(|s| DecodingKey::from_secret(s))
                .ok_or(JwtError::MissingKey),
            Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512 => self
                .rsa_public_pems
                .first()
                .map(|p| DecodingKey::from_rsa_pem(p))
                .transpose()?
                .ok_or(JwtError::MissingKey),
            Algorithm::ES256 | Algorithm::ES384 | Algorithm::ES512 => self
                .ecdsa_public_pems
                .first()
                .map(|p| DecodingKey::from_ec_pem(p))
                .transpose()?
                .ok_or(JwtError::MissingKey),
            _ => Err(JwtError::UnsupportedAlgorithm(alg)),
        }
    }
}

fn allowed_algorithms() -> HashSet<Algorithm> {
    [
        Algorithm::HS256,
        Algorithm::HS384,
        Algorithm::HS512,
        Algorithm::RS256,
        Algorithm::RS384,
        Algorithm::RS512,
        Algorithm::ES256,
        Algorithm::ES384,
        Algorithm::ES512,
    ]
    .into_iter()
    .collect()
}

#[cfg(test)]
mod tests {
    use super::*;
    use http::HeaderValue;
    use jsonwebtoken::{encode, EncodingKey, Header};

    #[test]
    fn verifies_hs256_from_headers() {
        let mut headers = HeaderMap::new();
        let secret = b"test-secret";
        let claims = UserClaims {
            sub: "user-1".to_string(),
            email: Some("a@b.c".to_string()),
            name: None,
        };
        let token = encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret(secret),
        )
        .unwrap();
        headers.insert(
            AUTHORIZATION,
            HeaderValue::from_str(&format!("Bearer {token}")).unwrap(),
        );
        let verifier = JwtVerifier {
            hs256_secrets: &[secret.as_slice()],
            rsa_public_pems: &[],
            ecdsa_public_pems: &[],
        };
        let user = verifier.verify_request(&headers).unwrap();
        assert_eq!(user.user_id, "user-1");
        assert_eq!(user.email.as_deref(), Some("a@b.c"));
    }
}
