use axum::{
    body::Body,
    extract::Request,
    http::{header::AUTHORIZATION, StatusCode},
    response::{IntoResponse, Response},
    routing::get,
    Router,
};
use jsonwebtoken::{decode, decode_header, Algorithm, DecodingKey, Validation};
use serde::{Deserialize, Serialize};
use std::sync::Arc;

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct UserInfo {
    pub sub: String,
    pub email: Option<String>,
    pub name: Option<String>,
    pub roles: Vec<String>,
    pub raw_claims: serde_json::Value,
}

#[derive(Debug, Deserialize, Serialize)]
struct Claims {
    sub: String,
    #[serde(default)]
    email: Option<String>,
    #[serde(default)]
    name: Option<String>,
    #[serde(default)]
    roles: Vec<String>,
    #[serde(flatten)]
    extra: serde_json::Map<String, serde_json::Value>,
}

pub struct JwtVerifier {
    hmac_secrets: Vec<Vec<u8>>,
    rsa_public_keys_pem: Vec<Vec<u8>>,
    ec_public_keys_pem: Vec<Vec<u8>>,
    allowed_algorithms: Vec<Algorithm>,
}

impl JwtVerifier {
    pub fn new() -> Self {
        Self {
            hmac_secrets: Vec::new(),
            rsa_public_keys_pem: Vec::new(),
            ec_public_keys_pem: Vec::new(),
            allowed_algorithms: vec![
                Algorithm::HS256,
                Algorithm::HS384,
                Algorithm::HS512,
                Algorithm::RS256,
                Algorithm::RS384,
                Algorithm::RS512,
                Algorithm::ES256,
                Algorithm::ES384,
            ],
        }
    }

    pub fn with_hmac_secret(mut self, secret: impl Into<Vec<u8>>) -> Self {
        self.hmac_secrets.push(secret.into());
        self
    }

    pub fn with_rsa_pem(mut self, pem: impl Into<Vec<u8>>) -> Self {
        self.rsa_public_keys_pem.push(pem.into());
        self
    }

    pub fn with_ec_pem(mut self, pem: impl Into<Vec<u8>>) -> Self {
        self.ec_public_keys_pem.push(pem.into());
        self
    }

    pub fn with_allowed_algorithms(mut self, algs: Vec<Algorithm>) -> Self {
        self.allowed_algorithms = algs;
        self
    }

    fn validation_for(&self, alg: Algorithm) -> Validation {
        let mut v = Validation::new(alg);
        v.algorithms = self.allowed_algorithms.clone();
        v
    }

    fn try_hmac(&self, token: &str, alg: Algorithm) -> Option<Claims> {
        if !matches!(
            alg,
            Algorithm::HS256 | Algorithm::HS384 | Algorithm::HS512
        ) {
            return None;
        }
        let v = self.validation_for(alg);
        for secret in &self.hmac_secrets {
            let key = DecodingKey::from_secret(secret);
            if let Ok(t) = decode::<Claims>(token, &key, &v) {
                return Some(t.claims);
            }
        }
        None
    }

    fn try_rsa(&self, token: &str, alg: Algorithm) -> Option<Claims> {
        if !matches!(
            alg,
            Algorithm::RS256 | Algorithm::RS384 | Algorithm::RS512
        ) {
            return None;
        }
        let v = self.validation_for(alg);
        for pem in &self.rsa_public_keys_pem {
            if let Ok(key) = DecodingKey::from_rsa_pem(pem) {
                if let Ok(t) = decode::<Claims>(token, &key, &v) {
                    return Some(t.claims);
                }
            }
        }
        None
    }

    fn try_ec(&self, token: &str, alg: Algorithm) -> Option<Claims> {
        if !matches!(alg, Algorithm::ES256 | Algorithm::ES384) {
            return None;
        }
        let v = self.validation_for(alg);
        for pem in &self.ec_public_keys_pem {
            if let Ok(key) = DecodingKey::from_ec_pem(pem) {
                if let Ok(t) = decode::<Claims>(token, &key, &v) {
                    return Some(t.claims);
                }
            }
        }
        None
    }

    pub fn verify_token(&self, token: &str) -> Result<UserInfo, String> {
        let header = decode_header(token).map_err(|e| e.to_string())?;
        let alg = header.alg;
        if !self.allowed_algorithms.contains(&alg) {
            return Err(format!("algorithm {:?} not allowed", alg));
        }
        let claims = self
            .try_hmac(token, alg)
            .or_else(|| self.try_rsa(token, alg))
            .or_else(|| self.try_ec(token, alg))
            .ok_or_else(|| "signature verification failed for all configured keys".to_string())?;
        let raw_claims = serde_json::to_value(&claims).map_err(|e| e.to_string())?;
        Ok(UserInfo {
            sub: claims.sub,
            email: claims.email,
            name: claims.name,
            roles: claims.roles,
            raw_claims,
        })
    }
}

pub fn bearer_token_from_request(req: &Request<Body>) -> Result<&str, StatusCode> {
    let auth = req
        .headers()
        .get(AUTHORIZATION)
        .and_then(|v| v.to_str().ok())
        .ok_or(StatusCode::UNAUTHORIZED)?;
    let prefix = "Bearer ";
    if !auth.starts_with(prefix) {
        return Err(StatusCode::UNAUTHORIZED);
    }
    let token = auth[prefix.len()..].trim();
    if token.is_empty() {
        return Err(StatusCode::UNAUTHORIZED);
    }
    Ok(token)
}

async fn protected(
    axum::extract::State(verifier): axum::extract::State<Arc<JwtVerifier>>,
    req: Request<Body>,
) -> Result<Response, StatusCode> {
    let token = bearer_token_from_request(&req)?;
    let user = verifier
        .verify_token(token)
        .map_err(|_| StatusCode::UNAUTHORIZED)?;
    let body = serde_json::to_string(&user).map_err(|_| StatusCode::INTERNAL_SERVER_ERROR)?;
    Ok((StatusCode::OK, body).into_response())
}

#[tokio::main]
async fn main() {
    let hmac = std::env::var("JWT_HMAC_SECRET").unwrap_or_else(|_| "dev-hmac-secret".into());
    let rsa_pem = std::env::var("JWT_RSA_PEM").unwrap_or_default();
    let ec_pem = std::env::var("JWT_EC_PEM").unwrap_or_default();

    let mut verifier = JwtVerifier::new().with_hmac_secret(hmac.as_bytes());
    if !rsa_pem.is_empty() {
        verifier = verifier.with_rsa_pem(rsa_pem.into_bytes());
    }
    if !ec_pem.is_empty() {
        verifier = verifier.with_ec_pem(ec_pem.into_bytes());
    }

    let app = Router::new()
        .route("/me", get(protected))
        .with_state(Arc::new(verifier));

    let listener = tokio::net::TcpListener::bind("127.0.0.1:3000")
        .await
        .expect("bind");
    axum::serve(listener, app).await.expect("serve");
}
