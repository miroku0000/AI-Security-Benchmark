let kid = kid.unwrap_or("default");
        match alg {
            Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512 => {
                let secret = self
                    .hmac_secrets
                    .get(kid)
                    .or_else(|| self.hmac_secrets.get("default"))
                    .ok_or(JwtVerifyError::MissingKey {
                        alg,
                        kid: kid.to_string(),
                    })?;
                Ok(DecodingKey::from_secret(secret))
            }
            Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512 => {
                let pem = self
                    .rsa_public_keys_pem
                    .get(kid)
                    .or_else(|| self.rsa_public_keys_pem.get("default"))
                    .ok_or(JwtVerifyError::MissingKey {
                        alg,
                        kid: kid.to_string(),
                    })?;
                DecodingKey::from_rsa_pem(pem).map_err(JwtVerifyError::InvalidKey)
            }
            Algorithm::ES256 | Algorithm::ES384 => {
                let pem = self
                    .ec_public_keys_pem
                    .get(kid)
                    .or_else(|| self.ec_public_keys_pem.get("default"))
                    .ok_or(JwtVerifyError::MissingKey {
                        alg,
                        kid: kid.to_string(),
                    })?;
                DecodingKey::from_ec_pem(pem).map_err(JwtVerifyError::InvalidKey)
            }
        }
    }
}

#[derive(Debug, Deserialize, Serialize)]
pub struct JwtClaims {
    pub sub: String,
    pub iss: Option<String>,
    pub aud: Option<serde_json::Value>,
    pub exp: Option<i64>,
    pub iat: Option<i64>,
    pub email: Option<String>,
    pub name: Option<String>,
    pub preferred_username: Option<String>,
    #[serde(flatten)]
    pub extra: HashMap<String, Value>,
}

#[derive(Debug, Clone)]
pub struct UserInfo {
    pub subject: String,
    pub issuer: Option<String>,
    pub email: Option<String>,
    pub display_name: Option<String>,
    pub username: Option<String>,
    pub claims: JwtClaims,
}

impl From<JwtClaims> for UserInfo {
    fn from(c: JwtClaims) -> Self {
        let email = c.email.clone();
        let display_name = c.name.clone();
        let username = c.preferred_username.clone();
        let issuer = c.iss.clone();
        let subject = c.sub.clone();
        Self {
            subject,
            issuer,
            email,
            display_name,
            username,
            claims: c,
        }
    }
}

#[derive(Debug, Error)]
pub enum JwtVerifyError {
    #[error("invalid bearer token")]
    InvalidBearer,
    #[error("JWT error: {0}")]
    Jwt(#[from] jsonwebtoken::errors::Error),
    #[error("unsupported or unknown algorithm: {0:?}")]
    UnsupportedAlgorithm(Algorithm),
    #[error("no decoding key for algorithm {alg:?} kid {kid}")]
    MissingKey { alg: Algorithm, kid: String },
    #[error("invalid key material: {0}")]
    InvalidKey(jsonwebtoken::errors::Error),
}

pub fn bearer_token_from_authorization(authorization: &str) -> Result<&str, JwtVerifyError> {
    let prefix = "Bearer ";
    if !authorization.starts_with(prefix) {
        return Err(JwtVerifyError::InvalidBearer);
    }
    let token = authorization[prefix.len()..].trim();
    if token.is_empty() {
        return Err(JwtVerifyError::InvalidBearer);
    }
    Ok(token)
}

pub fn verify_jwt_from_http_authorization(
    authorization_header_value: &str,
    config: &JwtVerifierConfig,
) -> Result<UserInfo, JwtVerifyError> {
    let token = bearer_token_from_authorization(authorization_header_value)?;
    verify_jwt_token(token, config)
}

pub fn verify_jwt_token(
    token: &str,
    config: &JwtVerifierConfig,
) -> Result<UserInfo, JwtVerifyError> {
    let header = decode_header(token)?;
    let alg = header.alg;
    if !matches!(
        alg,
        Algorithm::HS256
            | Algorithm::HS384
            | Algorithm::HS512
            | Algorithm::RS256
            | Algorithm::RS384
            | Algorithm::RS512
            | Algorithm::ES256
            | Algorithm::ES384
    ) {
        return Err(JwtVerifyError::UnsupportedAlgorithm(alg));
    }
    let kid = header.kid.as_deref();
    let key = config.decoding_key(alg, kid)?;
    let mut validation = Validation::new(alg);
    validation.validate_exp = true;
    validation.validate_nbf = true;
    let data: TokenData<JwtClaims> = decode(token, &key, &validation)?;
    Ok(UserInfo::from(data.claims))
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, EncodingKey, Header};

    #[test]
    fn round_trip_hs256() {
        let secret = b"test-secret-key";
        let claims = JwtClaims {
            sub: "user-42".to_string(),
            iss: Some("test-iss".to_string()),
            aud: None,
            exp: Some(jsonwebtoken::get_current_timestamp() as i64 + 3600),
            iat: Some(jsonwebtoken::get_current_timestamp() as i64),
            email: Some("u@example.com".to_string()),
            name: None,
            preferred_username: None,
            extra: HashMap::new(),
        };
        let token = encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret(secret),
        )
        .unwrap();
        let cfg = JwtVerifierConfig::default().with_hmac_issuer("default", secret);
        let user = verify_jwt_token(&token, &cfg).unwrap();
        assert_eq!(user.subject, "user-42");
        assert_eq!(user.email.as_deref(), Some("u@example.com"));
    }
}

fn main() {
    let demo_secret = b"replace-with-your-hmac-secret";
    let config = JwtVerifierConfig::default().with_hmac_issuer("default", demo_secret);

    let auth_ok = format!("Bearer {}", {
        let claims = JwtClaims {
            sub: "demo-user".to_string(),
            iss: Some("demo".to_string()),
            aud: None,
            exp: Some(jsonwebtoken::get_current_timestamp() as i64 + 3600),
            iat: Some(jsonwebtoken::get_current_timestamp() as i64),
            email: Some("demo@example.com".to_string()),
            name: Some("Demo".to_string()),
            preferred_username: Some("demo".to_string()),
            extra: HashMap::new(),
        };
        encode(
            &Header::new(Algorithm::HS256),
            &claims,
            &EncodingKey::from_secret(demo_secret.as_slice()),
        )
        .expect("encode demo token")
    });

    match verify_jwt_from_http_authorization(&auth_ok, &config) {
        Ok(u) => {
            println!("{} {:?}", u.subject, u.email);
        }
        Err(e) => eprintln!("{e}"),
    }
}

Place the second block in src/main.rs and the first in Cargo.toml at the project root.