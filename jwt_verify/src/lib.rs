use http::header::AUTHORIZATION;
use http::HeaderMap;
use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, TokenData, Validation};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use thiserror::Error;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct JwtClaims {
    pub sub: String,
    #[serde(default)]
    pub iss: Option<String>,
    #[serde(default)]
    pub aud: Option<serde_json::Value>,
    #[serde(default)]
    pub email: Option<String>,
    #[serde(default)]
    pub name: Option<String>,
    #[serde(default)]
    pub preferred_username: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct UserInfo {
    pub subject: String,
    pub email: Option<String>,
    pub name: Option<String>,
    pub issuer: Option<String>,
    pub raw_claims: JwtClaims,
}

#[derive(Debug, Clone, Default)]
pub struct JwtVerificationKeys {
    pub hmac_secret: Option<Vec<u8>>,
    pub rsa_public_pem: Option<Vec<u8>>,
    pub ec_public_pem: Option<Vec<u8>>,
    pub ed_public_pem: Option<Vec<u8>>,
    pub rsa_by_kid: HashMap<String, Vec<u8>>,
}

impl JwtVerificationKeys {
    fn decoding_key_for(
        &self,
        alg: Algorithm,
        kid: Option<&str>,
    ) -> Result<DecodingKey, JwtVerifyError> {
        match alg {
            Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512 => self
                .hmac_secret
                .as_ref()
                .map(|s| DecodingKey::from_secret(s.as_slice()))
                .ok_or(JwtVerifyError::MissingKeyForAlgorithm(alg)),
            Algorithm::RS256
            | Algorithm::RS384
            | Algorithm::RS512
            | Algorithm::PS256
            | Algorithm::PS384
            | Algorithm::PS512 => {
                let pem = kid
                    .and_then(|k| self.rsa_by_kid.get(k))
                    .or_else(|| self.rsa_public_pem.as_ref())
                    .ok_or(JwtVerifyError::MissingKeyForAlgorithm(alg))?;
                DecodingKey::from_rsa_pem(pem).map_err(JwtVerifyError::Jwt)
            }
            Algorithm::ES256 | Algorithm::ES384 => {
                let pem = self
                    .ec_public_pem
                    .as_ref()
                    .ok_or(JwtVerifyError::MissingKeyForAlgorithm(alg))?;
                DecodingKey::from_ec_pem(pem).map_err(JwtVerifyError::Jwt)
            }
            Algorithm::EdDSA => {
                let pem = self
                    .ed_public_pem
                    .as_ref()
                    .ok_or(JwtVerifyError::MissingKeyForAlgorithm(alg))?;
                DecodingKey::from_ed_pem(pem).map_err(JwtVerifyError::Jwt)
            }
        }
    }
}

#[derive(Debug, Error)]
pub enum JwtVerifyError {
    #[error("missing Authorization header")]
    MissingAuthorization,
    #[error("invalid Authorization header")]
    InvalidAuthorization,
    #[error("no verification key configured for algorithm {0:?}")]
    MissingKeyForAlgorithm(Algorithm),
    #[error("JWT error: {0}")]
    Jwt(#[from] jsonwebtoken::errors::Error),
}

pub fn bearer_token_from_headers(headers: &HeaderMap) -> Result<&str, JwtVerifyError> {
    let raw = headers
        .get(AUTHORIZATION)
        .ok_or(JwtVerifyError::MissingAuthorization)?
        .to_str()
        .map_err(|_| JwtVerifyError::InvalidAuthorization)?;
    let token = raw
        .strip_prefix("Bearer ")
        .or_else(|| raw.strip_prefix("bearer "))
        .ok_or(JwtVerifyError::InvalidAuthorization)?;
    let token = token.trim();
    if token.is_empty() {
        return Err(JwtVerifyError::InvalidAuthorization);
    }
    Ok(token)
}

pub fn verify_jwt_token(
    token: &str,
    keys: &JwtVerificationKeys,
    validation: &Validation,
) -> Result<UserInfo, JwtVerifyError> {
    let header = decode_header(token)?;
    let alg = header.alg;
    let kid = header.kid.as_deref();
    let decoding_key = keys.decoding_key_for(alg, kid)?;

    let mut val = validation.clone();
    val.algorithms = vec![alg];

    let data: TokenData<JwtClaims> = decode(token, &decoding_key, &val)?;

    let claims = data.claims;
    let email = claims.email.clone().or(claims.preferred_username.clone());
    let name = claims.name.clone();

    Ok(UserInfo {
        subject: claims.sub.clone(),
        email,
        name,
        issuer: claims.iss.clone(),
        raw_claims: claims,
    })
}

pub fn verify_jwt_from_http_request(
    headers: &HeaderMap,
    keys: &JwtVerificationKeys,
    validation: &Validation,
) -> Result<UserInfo, JwtVerifyError> {
    let token = bearer_token_from_headers(headers)?;
    verify_jwt_token(token, keys, validation)
}
