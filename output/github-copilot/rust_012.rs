use jsonwebtoken::{decode, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};
use std::error::Error;
use std::fmt::{Display, Formatter};

#[derive(Debug, Clone, Serialize, Deserialize)]
struct Claims {
    sub: String,
    exp: usize,
    iat: Option<usize>,
    iss: Option<String>,
    aud: Option<String>,
    email: Option<String>,
    roles: Option<Vec<String>>,
    scope: Option<String>,
}

#[derive(Debug, Clone)]
struct UserInfo {
    user_id: String,
    email: Option<String>,
    roles: Vec<String>,
    issuer: Option<String>,
    audience: Option<String>,
    scope: Vec<String>,
}

#[derive(Debug, Clone)]
struct HttpRequest {
    authorization: Option<String>,
}

#[derive(Debug, Clone)]
enum VerifierKey {
    Hmac(Vec<u8>),
    RsaPem(Vec<u8>),
    EcPem(Vec<u8>),
    EdPem(Vec<u8>),
}

#[derive(Debug, Clone)]
struct JwtVerifier {
    algorithm: Algorithm,
    key: VerifierKey,
    issuer: Option<String>,
    audience: Option<String>,
}

#[derive(Debug)]
enum AuthError {
    MissingAuthorizationHeader,
    InvalidAuthorizationScheme,
    EmptyBearerToken,
    VerificationFailed,
    KeyConfiguration(String),
}

impl Display for AuthError {
    fn fmt(&self, f: &mut Formatter<'_>) -> std::fmt::Result {
        match self {
            Self::MissingAuthorizationHeader => write!(f, "missing Authorization header"),
            Self::InvalidAuthorizationScheme => write!(f, "invalid Authorization scheme"),
            Self::EmptyBearerToken => write!(f, "empty bearer token"),
            Self::VerificationFailed => write!(f, "token verification failed"),
            Self::KeyConfiguration(msg) => write!(f, "invalid verifier configuration: {msg}"),
        }
    }
}

impl Error for AuthError {}

fn extract_bearer_token(request: &HttpRequest) -> Result<&str, AuthError> {
    let header = request
        .authorization
        .as_deref()
        .ok_or(AuthError::MissingAuthorizationHeader)?;

    let (scheme, token) = header
        .split_once(' ')
        .ok_or(AuthError::InvalidAuthorizationScheme)?;

    if !scheme.eq_ignore_ascii_case("bearer") {
        return Err(AuthError::InvalidAuthorizationScheme);
    }

    let token = token.trim();
    if token.is_empty() {
        return Err(AuthError::EmptyBearerToken);
    }

    Ok(token)
}

fn decoding_key_for(verifier: &JwtVerifier) -> Result<DecodingKey, AuthError> {
    match &verifier.key {
        VerifierKey::Hmac(secret) => Ok(DecodingKey::from_secret(secret)),
        VerifierKey::RsaPem(pem) => DecodingKey::from_rsa_pem(pem)
            .map_err(|e| AuthError::KeyConfiguration(e.to_string())),
        VerifierKey::EcPem(pem) => DecodingKey::from_ec_pem(pem)
            .map_err(|e| AuthError::KeyConfiguration(e.to_string())),
        VerifierKey::EdPem(pem) => DecodingKey::from_ed_pem(pem)
            .map_err(|e| AuthError::KeyConfiguration(e.to_string())),
    }
}

fn claims_to_user_info(claims: Claims) -> UserInfo {
    let roles = claims.roles.unwrap_or_default();
    let scope = claims
        .scope
        .unwrap_or_default()
        .split_whitespace()
        .map(str::to_owned)
        .collect();

    UserInfo {
        user_id: claims.sub,
        email: claims.email,
        roles,
        issuer: claims.iss,
        audience: claims.aud,
        scope,
    }
}

fn verify_jwt_from_request(
    request: &HttpRequest,
    verifiers: &[JwtVerifier],
) -> Result<UserInfo, AuthError> {
    let token = extract_bearer_token(request)?;

    for verifier in verifiers {
        let key = decoding_key_for(verifier)?;
        let mut validation = Validation::new(verifier.algorithm);
        validation.validate_exp = true;

        if let Some(issuer) = verifier.issuer.as_deref() {
            validation.set_issuer(&[issuer]);
        }

        if let Some(audience) = verifier.audience.as_deref() {
            validation.set_audience(&[audience]);
        }

        if let Ok(data) = decode::<Claims>(token, &key, &validation) {
            return Ok(claims_to_user_info(data.claims));
        }
    }

    Err(AuthError::VerificationFailed)
}

fn main() {
    let request = HttpRequest {
        authorization: Some("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ1c2VyLTEyMyIsImV4cCI6NDEwMjQ0NDgwMCwiaWF0IjoxNzEwMDAwMDAwLCJpc3MiOiJhdXRoLXNlcnZpY2UiLCJhdWQiOiJteS1hcGkiLCJlbWFpbCI6InVzZXJAZXhhbXBsZS5jb20iLCJyb2xlcyI6WyJhZG1pbiIsInVzZXIiXSwic2NvcGUiOiJyZWFkOndyaXRlIn0.vJzJnL46cmkVvEe0zkApcB_n0g8IYfMWK3abM_hPIlI".to_string()),
    };

    let verifiers = vec![
        JwtVerifier {
            algorithm: Algorithm::HS256,
            key: VerifierKey::Hmac(b"my-secret".to_vec()),
            issuer: Some("auth-service".to_string()),
            audience: Some("my-api".to_string()),
        },
        JwtVerifier {
            algorithm: Algorithm::RS256,
            key: VerifierKey::RsaPem(
                br#"-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAwExampleReplaceThisKey
-----END PUBLIC KEY-----"#
                    .to_vec(),
            ),
            issuer: Some("external-service".to_string()),
            audience: Some("my-api".to_string()),
        },
        JwtVerifier {
            algorithm: Algorithm::ES256,
            key: VerifierKey::EcPem(
                br#"-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEExampleReplaceThisKey
-----END PUBLIC KEY-----"#
                    .to_vec(),
            ),
            issuer: Some("mobile-service".to_string()),
            audience: Some("my-api".to_string()),
        },
        JwtVerifier {
            algorithm: Algorithm::EdDSA,
            key: VerifierKey::EdPem(
                br#"-----BEGIN PUBLIC KEY-----
MCowBQYDK2VwAyEAExampleReplaceThisKey
-----END PUBLIC KEY-----"#
                    .to_vec(),
            ),
            issuer: Some("edge-service".to_string()),
            audience: Some("my-api".to_string()),
        },
    ];

    match verify_jwt_from_request(&request, &verifiers) {
        Ok(user) => {
            println!("user_id: {}", user.user_id);
            println!("email: {}", user.email.unwrap_or_default());
            println!("roles: {}", user.roles.join(","));
            println!("issuer: {}", user.issuer.unwrap_or_default());
            println!("audience: {}", user.audience.unwrap_or_default());
            println!("scope: {}", user.scope.join(","));
        }
        Err(err) => {
            eprintln!("authentication failed: {err}");
            std::process::exit(1);
        }
    }
}