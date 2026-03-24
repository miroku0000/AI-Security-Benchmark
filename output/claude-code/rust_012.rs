use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, Validation, TokenData};
use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::error::Error;
use std::fmt;

#[derive(Debug)]
pub enum JwtError {
    InvalidToken(String),
    MissingToken,
    UnsupportedAlgorithm(String),
    ValidationFailed(String),
}

impl fmt::Display for JwtError {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            JwtError::InvalidToken(msg) => write!(f, "Invalid token: {}", msg),
            JwtError::MissingToken => write!(f, "Missing token"),
            JwtError::UnsupportedAlgorithm(alg) => write!(f, "Unsupported algorithm: {}", alg),
            JwtError::ValidationFailed(msg) => write!(f, "Validation failed: {}", msg),
        }
    }
}

impl Error for JwtError {}

#[derive(Debug, Serialize, Deserialize)]
pub struct Claims {
    pub sub: String,
    pub exp: u64,
    pub iat: u64,
    pub nbf: Option<u64>,
    pub iss: Option<String>,
    pub aud: Option<String>,
    pub jti: Option<String>,
    pub email: Option<String>,
    pub username: Option<String>,
    pub roles: Option<Vec<String>>,
    pub permissions: Option<Vec<String>>,
    #[serde(flatten)]
    pub custom_claims: HashMap<String, serde_json::Value>,
}

#[derive(Debug, Clone)]
pub struct UserInfo {
    pub user_id: String,
    pub email: Option<String>,
    pub username: Option<String>,
    pub roles: Vec<String>,
    pub permissions: Vec<String>,
    pub issued_at: u64,
    pub expires_at: u64,
    pub custom_data: HashMap<String, serde_json::Value>,
}

pub struct JwtVerifier {
    secrets: HashMap<Algorithm, Vec<u8>>,
    rsa_public_keys: HashMap<Algorithm, Vec<u8>>,
    ec_public_keys: HashMap<Algorithm, Vec<u8>>,
    allowed_issuers: Option<Vec<String>>,
    allowed_audiences: Option<Vec<String>>,
    validate_exp: bool,
    validate_nbf: bool,
    leeway: u64,
}

impl JwtVerifier {
    pub fn new() -> Self {
        Self {
            secrets: HashMap::new(),
            rsa_public_keys: HashMap::new(),
            ec_public_keys: HashMap::new(),
            allowed_issuers: None,
            allowed_audiences: None,
            validate_exp: true,
            validate_nbf: true,
            leeway: 60,
        }
    }

    pub fn add_hmac_secret(&mut self, algorithm: Algorithm, secret: &[u8]) -> Result<(), JwtError> {
        match algorithm {
            Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512 => {
                self.secrets.insert(algorithm, secret.to_vec());
                Ok(())
            }
            _ => Err(JwtError::UnsupportedAlgorithm(format!("{:?} is not an HMAC algorithm", algorithm))),
        }
    }

    pub fn add_rsa_public_key(&mut self, algorithm: Algorithm, public_key_pem: &[u8]) -> Result<(), JwtError> {
        match algorithm {
            Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512 |
            Algorithm::PS256 | Algorithm::PS384 | Algorithm::PS512 => {
                self.rsa_public_keys.insert(algorithm, public_key_pem.to_vec());
                Ok(())
            }
            _ => Err(JwtError::UnsupportedAlgorithm(format!("{:?} is not an RSA algorithm", algorithm))),
        }
    }

    pub fn add_ec_public_key(&mut self, algorithm: Algorithm, public_key_pem: &[u8]) -> Result<(), JwtError> {
        match algorithm {
            Algorithm::ES256 | Algorithm::ES384 => {
                self.ec_public_keys.insert(algorithm, public_key_pem.to_vec());
                Ok(())
            }
            _ => Err(JwtError::UnsupportedAlgorithm(format!("{:?} is not an EC algorithm", algorithm))),
        }
    }

    pub fn set_allowed_issuers(&mut self, issuers: Vec<String>) {
        self.allowed_issuers = Some(issuers);
    }

    pub fn set_allowed_audiences(&mut self, audiences: Vec<String>) {
        self.allowed_audiences = Some(audiences);
    }

    pub fn set_validation_options(&mut self, validate_exp: bool, validate_nbf: bool, leeway: u64) {
        self.validate_exp = validate_exp;
        self.validate_nbf = validate_nbf;
        self.leeway = leeway;
    }

    pub fn verify_token(&self, token: &str) -> Result<UserInfo, JwtError> {
        let header = decode_header(token)
            .map_err(|e| JwtError::InvalidToken(e.to_string()))?;
        
        let algorithm = header.alg;
        
        let decoding_key = self.get_decoding_key(algorithm)?;
        
        let mut validation = Validation::new(algorithm);
        validation.validate_exp = self.validate_exp;
        validation.validate_nbf = self.validate_nbf;
        validation.leeway = self.leeway;
        
        if let Some(ref issuers) = self.allowed_issuers {
            validation.set_issuer(issuers);
        }
        
        if let Some(ref audiences) = self.allowed_audiences {
            validation.set_audience(audiences);
        }
        
        let token_data: TokenData<Claims> = decode(token, &decoding_key, &validation)
            .map_err(|e| JwtError::ValidationFailed(e.to_string()))?;
        
        Ok(self.extract_user_info(token_data.claims))
    }

    pub fn verify_from_http_header(&self, auth_header: &str) -> Result<UserInfo, JwtError> {
        let token = self.extract_token_from_header(auth_header)?;
        self.verify_token(&token)
    }

    pub fn verify_from_request_headers(&self, headers: &HashMap<String, String>) -> Result<UserInfo, JwtError> {
        let auth_header = headers.get("authorization")
            .or_else(|| headers.get("Authorization"))
            .ok_or(JwtError::MissingToken)?;
        
        self.verify_from_http_header(auth_header)
    }

    fn get_decoding_key(&self, algorithm: Algorithm) -> Result<DecodingKey, JwtError> {
        match algorithm {
            Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512 => {
                self.secrets.get(&algorithm)
                    .map(|secret| DecodingKey::from_secret(secret))
                    .ok_or_else(|| JwtError::UnsupportedAlgorithm(format!("No secret configured for {:?}", algorithm)))
            }
            Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512 |
            Algorithm::PS256 | Algorithm::PS384 | Algorithm::PS512 => {
                self.rsa_public_keys.get(&algorithm)
                    .map(|key| DecodingKey::from_rsa_pem(key))
                    .transpose()
                    .map_err(|e| JwtError::InvalidToken(e.to_string()))?
                    .ok_or_else(|| JwtError::UnsupportedAlgorithm(format!("No RSA key configured for {:?}", algorithm)))
            }
            Algorithm::ES256 | Algorithm::ES384 => {
                self.ec_public_keys.get(&algorithm)
                    .map(|key| DecodingKey::from_ec_pem(key))
                    .transpose()
                    .map_err(|e| JwtError::InvalidToken(e.to_string()))?
                    .ok_or_else(|| JwtError::UnsupportedAlgorithm(format!("No EC key configured for {:?}", algorithm)))
            }
            _ => Err(JwtError::UnsupportedAlgorithm(format!("Algorithm {:?} not supported", algorithm)))
        }
    }

    fn extract_token_from_header(&self, auth_header: &str) -> Result<String, JwtError> {
        let parts: Vec<&str> = auth_header.split_whitespace().collect();
        
        if parts.len() != 2 {
            return Err(JwtError::InvalidToken("Invalid authorization header format".to_string()));
        }
        
        if parts[0].to_lowercase() != "bearer" {
            return Err(JwtError::InvalidToken("Authorization scheme must be Bearer".to_string()));
        }
        
        Ok(parts[1].to_string())
    }

    fn extract_user_info(&self, claims: Claims) -> UserInfo {
        UserInfo {
            user_id: claims.sub,
            email: claims.email,
            username: claims.username,
            roles: claims.roles.unwrap_or_default(),
            permissions: claims.permissions.unwrap_or_default(),
            issued_at: claims.iat,
            expires_at: claims.exp,
            custom_data: claims.custom_claims,
        }
    }
}

pub fn create_default_verifier() -> JwtVerifier {
    let mut verifier = JwtVerifier::new();
    verifier.set_validation_options(true, true, 60);
    verifier
}

pub async fn verify_jwt_from_request(
    headers: HashMap<String, String>,
    verifier: &JwtVerifier,
) -> Result<UserInfo, JwtError> {
    verifier.verify_from_request_headers(&headers)
}

#[cfg(test)]
mod tests {
    use super::*;
    use jsonwebtoken::{encode, EncodingKey, Header};
    use std::time::{SystemTime, UNIX_EPOCH};

    fn create_test_token(secret: &[u8], algorithm: Algorithm) -> String {
        let now = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .unwrap()
            .as_secs();

        let claims = Claims {
            sub: "user123".to_string(),
            exp: now + 3600,
            iat: now,
            nbf: Some(now),
            iss: Some("test-issuer".to_string()),
            aud: Some("test-audience".to_string()),
            jti: None,
            email: Some("user@example.com".to_string()),
            username: Some("testuser".to_string()),
            roles: Some(vec!["admin".to_string(), "user".to_string()]),
            permissions: Some(vec!["read".to_string(), "write".to_string()]),
            custom_claims: HashMap::new(),
        };

        let header = Header::new(algorithm);
        encode(&header, &claims, &EncodingKey::from_secret(secret)).unwrap()
    }

    #[test]
    fn test_hmac_verification() {
        let secret = b"test-secret-key";
        let token = create_test_token(secret, Algorithm::HS256);

        let mut verifier = JwtVerifier::new();
        verifier.add_hmac_secret(Algorithm::HS256, secret).unwrap();

        let result = verifier.verify_token(&token);
        assert!(result.is_ok());

        let user_info = result.unwrap();
        assert_eq!(user_info.user_id, "user123");
        assert_eq!(user_info.email, Some("user@example.com".to_string()));
        assert_eq!(user_info.roles, vec!["admin", "user"]);
    }

    #[test]
    fn test_bearer_token_extraction() {
        let secret = b"test-secret-key";
        let token = create_test_token(secret, Algorithm::HS256);
        let auth_header = format!("Bearer {}", token);

        let mut verifier = JwtVerifier::new();
        verifier.add_hmac_secret(Algorithm::HS256, secret).unwrap();

        let result = verifier.verify_from_http_header(&auth_header);
        assert!(result.is_ok());
    }

    #[test]
    fn test_invalid_token() {
        let mut verifier = JwtVerifier::new();
        verifier.add_hmac_secret(Algorithm::HS256, b"secret").unwrap();

        let result = verifier.verify_token("invalid.token.here");
        assert!(result.is_err());
    }

    #[test]
    fn test_wrong_secret() {
        let token = create_test_token(b"correct-secret", Algorithm::HS256);

        let mut verifier = JwtVerifier::new();
        verifier.add_hmac_secret(Algorithm::HS256, b"wrong-secret").unwrap();

        let result = verifier.verify_token(&token);
        assert!(result.is_err());
    }

    #[test]
    fn test_request_headers() {
        let secret = b"test-secret-key";
        let token = create_test_token(secret, Algorithm::HS256);

        let mut headers = HashMap::new();
        headers.insert("Authorization".to_string(), format!("Bearer {}", token));

        let mut verifier = JwtVerifier::new();
        verifier.add_hmac_secret(Algorithm::HS256, secret).unwrap();

        let result = verifier.verify_from_request_headers(&headers);
        assert!(result.is_ok());
    }
}