use jsonwebtoken::errors::ErrorKind;
use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, PartialEq, Eq, Serialize, Deserialize)]
pub struct UserInfo {
    pub sub: String,
    pub email: Option<String>,
    pub name: Option<String>,
    #[serde(default)]
    pub roles: Vec<String>,
}

#[derive(Debug, Clone, Deserialize, Serialize)]
pub struct Claims {
    pub sub: String,
    pub email: Option<String>,
    pub name: Option<String>,
    #[serde(default)]
    pub roles: Vec<String>,
    pub exp: Option<i64>,
    pub iat: Option<i64>,
}

#[derive(Debug, Clone, Default)]
pub struct JwtVerifierConfig {
    pub hmac_secrets: Vec<Vec<u8>>,
    pub rsa_public_keys_pem: Vec<String>,
    pub ecdsa_public_keys_pem: Vec<String>,
}

pub fn extract_bearer_token(authorization: Option<&str>) -> Option<&str> {
    authorization.and_then(|h| {
        let rest = h.strip_prefix("Bearer ").or_else(|| h.strip_prefix("bearer "))?;
        let t = rest.trim();
        if t.is_empty() {
            None
        } else {
            Some(t)
        }
    })
}

fn claims_to_user(c: Claims) -> UserInfo {
    UserInfo {
        sub: c.sub,
        email: c.email,
        name: c.name,
        roles: c.roles,
    }
}

fn try_decode_with_keys(
    token: &str,
    alg: Algorithm,
    keys: &[DecodingKey],
) -> Result<UserInfo, jsonwebtoken::errors::Error> {
    let mut validation = Validation::new(alg);
    validation.validate_exp = true;
    for key in keys {
        if let Ok(td) = decode::<Claims>(token, key, &validation) {
            return Ok(claims_to_user(td.claims));
        }
    }
    Err(jsonwebtoken::errors::Error::from(ErrorKind::InvalidSignature))
}

pub fn verify_jwt_from_authorization_header(
    authorization: Option<&str>,
    config: &JwtVerifierConfig,
) -> Result<UserInfo, jsonwebtoken::errors::Error> {
    let token = extract_bearer_token(authorization).ok_or_else(|| {
        jsonwebtoken::errors::Error::from(ErrorKind::InvalidToken)
    })?;
    verify_jwt_token(token, config)
}

pub fn verify_jwt_token(
    token: &str,
    config: &JwtVerifierConfig,
) -> Result<UserInfo, jsonwebtoken::errors::Error> {
    let header = decode_header(token)?;
    let alg = header.alg;

    match alg {
        Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512 => {
            let keys: Vec<DecodingKey> = config
                .hmac_secrets
                .iter()
                .map(|s| DecodingKey::from_secret(s.as_slice()))
                .collect();
            if keys.is_empty() {
                return Err(jsonwebtoken::errors::Error::from(
                    ErrorKind::InvalidAlgorithm,
                ));
            }
            try_decode_with_keys(token, alg, &keys)
        }
        Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512 => {
            let mut keys = Vec::new();
            for pem in &config.rsa_public_keys_pem {
                keys.push(DecodingKey::from_rsa_pem(pem.as_bytes())?);
            }
            if keys.is_empty() {
                return Err(jsonwebtoken::errors::Error::from(
                    ErrorKind::InvalidAlgorithm,
                ));
            }
            try_decode_with_keys(token, alg, &keys)
        }
        Algorithm::ES256 | Algorithm::ES384 => {
            let mut keys = Vec::new();
            for pem in &config.ecdsa_public_keys_pem {
                keys.push(DecodingKey::from_ec_pem(pem.as_bytes())?);
            }
            if keys.is_empty() {
                return Err(jsonwebtoken::errors::Error::from(
                    ErrorKind::InvalidAlgorithm,
                ));
            }
            try_decode_with_keys(token, alg, &keys)
        }
        _ => Err(jsonwebtoken::errors::Error::from(ErrorKind::InvalidAlgorithm)),
    }
}
