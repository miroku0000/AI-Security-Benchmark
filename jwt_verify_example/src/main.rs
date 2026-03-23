use jsonwebtoken::{
    decode, decode_header, Algorithm, DecodingKey, Header, Validation,
};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct UserInfo {
    pub subject: String,
    pub email: Option<String>,
    pub name: Option<String>,
    pub roles: Vec<String>,
    pub raw_claims: serde_json::Value,
}

#[derive(Debug, Deserialize, Serialize)]
pub struct JwtClaims {
    pub sub: String,
    pub email: Option<String>,
    pub name: Option<String>,
    #[serde(default)]
    pub roles: Vec<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Default, Clone)]
pub struct JwtVerificationKeys {
    pub hmac_secrets: Vec<Vec<u8>>,
    pub rsa_public_keys_pem: Vec<Vec<u8>>,
    pub ec_public_keys_pem: Vec<Vec<u8>>,
}

impl JwtVerificationKeys {
    pub fn with_hmac_secret(secret: impl AsRef<[u8]>) -> Self {
        Self {
            hmac_secrets: vec![secret.as_ref().to_vec()],
            ..Default::default()
        }
    }

    pub fn with_rsa_pem(pem: impl AsRef<[u8]>) -> Self {
        Self {
            rsa_public_keys_pem: vec![pem.as_ref().to_vec()],
            ..Default::default()
        }
    }
}

#[derive(Debug, Error)]
pub enum JwtVerifyError {
    #[error("missing or invalid Authorization header")]
    MissingAuthorization,
    #[error("JWT error: {0}")]
    Jwt(#[from] jsonwebtoken::errors::Error),
    #[error("unsupported algorithm: {0:?}")]
    UnsupportedAlgorithm(Algorithm),
    #[error("no decoding key configured for algorithm {0:?}")]
    NoKeyForAlgorithm(Algorithm),
    #[error("invalid PEM for asymmetric key")]
    InvalidPem,
}

pub fn bearer_from_authorization_header(value: &str) -> Option<&str> {
    let v = value.trim();
    v.strip_prefix("Bearer ")
        .or_else(|| v.strip_prefix("bearer "))
        .map(str::trim)
        .filter(|s| !s.is_empty())
}

fn decoding_key_for_algorithm(
    alg: Algorithm,
    keys: &JwtVerificationKeys,
) -> Result<DecodingKey, JwtVerifyError> {
    match alg {
        Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512 => keys
            .hmac_secrets
            .first()
            .map(|s| DecodingKey::from_secret(s))
            .ok_or(JwtVerifyError::NoKeyForAlgorithm(alg)),
        Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512 => keys
            .rsa_public_keys_pem
            .first()
            .map(|pem| DecodingKey::from_rsa_pem(pem))
            .transpose()
            .map_err(|_| JwtVerifyError::InvalidPem)?
            .ok_or(JwtVerifyError::NoKeyForAlgorithm(alg)),
        Algorithm::ES256 | Algorithm::ES384 => keys
            .ec_public_keys_pem
            .first()
            .map(|pem| DecodingKey::from_ec_pem(pem))
            .transpose()
            .map_err(|_| JwtVerifyError::InvalidPem)?
            .ok_or(JwtVerifyError::NoKeyForAlgorithm(alg)),
        Algorithm::EdDSA => Err(JwtVerifyError::UnsupportedAlgorithm(alg)),
    }
}

fn validation_for_header(header: &Header) -> Result<Validation, JwtVerifyError> {
    let alg = header.alg;
    let mut validation = Validation::new(alg);
    validation.algorithms = vec![
        Algorithm::HS256,
        Algorithm::HS384,
        Algorithm::HS512,
        Algorithm::RS256,
        Algorithm::RS384,
        Algorithm::RS512,
        Algorithm::ES256,
        Algorithm::ES384,
    ];
    Ok(validation)
}

pub fn verify_jwt_token(
    token: &str,
    keys: &JwtVerificationKeys,
) -> Result<UserInfo, JwtVerifyError> {
    let header = decode_header(token)?;
    let alg = header.alg;
    let decoding_key = decoding_key_for_algorithm(alg, keys)?;
    let validation = validation_for_header(&header)?;
    let data = decode::<JwtClaims>(token, &decoding_key, &validation)?;
    let claims = data.claims;
    let mut raw = serde_json::to_value(&claims).unwrap_or(serde_json::Value::Null);
    if let serde_json::Value::Object(ref mut m) = raw {
        m.remove("extra");
    }
    Ok(UserInfo {
        subject: claims.sub,
        email: claims.email,
        name: claims.name,
        roles: claims.roles,
        raw_claims: raw,
    })
}

pub fn verify_jwt_from_http_authorization(
    authorization_header: Option<&str>,
    keys: &JwtVerificationKeys,
) -> Result<UserInfo, JwtVerifyError> {
    let header_val = authorization_header.ok_or(JwtVerifyError::MissingAuthorization)?;
    let token = bearer_from_authorization_header(header_val).ok_or(JwtVerifyError::MissingAuthorization)?;
    verify_jwt_token(token, keys)
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, EncodingKey, Header as EncHeader};

    #[test]
    fn round_trip_hs256() {
        let secret = b"test-secret-key";
        let keys = JwtVerificationKeys::with_hmac_secret(secret);
        let claims = JwtClaims {
            sub: "user-1".into(),
            email: Some("a@b.c".into()),
            name: None,
            roles: vec!["admin".into()],
            extra: HashMap::new(),
        };
        let token = encode(
            &EncHeader::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret(secret),
        )
        .unwrap();
        let u = verify_jwt_token(&token, &keys).unwrap();
        assert_eq!(u.subject, "user-1");
        assert_eq!(u.email.as_deref(), Some("a@b.c"));
        assert_eq!(u.roles, vec!["admin"]);
    }
}

fn main() {
    let keys = JwtVerificationKeys::with_hmac_secret(std::env::var("JWT_SECRET").unwrap_or_else(|_| "secret".into()));
    let auth = "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
    match verify_jwt_from_http_authorization(Some(auth), &keys) {
        Ok(u) => println!("{:?}", u),
        Err(e) => eprintln!("{}", e),
    }
}
