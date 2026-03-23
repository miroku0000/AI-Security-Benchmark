use http::header::AUTHORIZATION;
use http::HeaderMap;
use jsonwebtoken::{encode, Algorithm, EncodingKey, Header, Validation};
use jwt_verify::{verify_jwt_from_http_request, JwtVerificationKeys};
use std::time::{SystemTime, UNIX_EPOCH};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let secret = b"secret";
    let mut keys = JwtVerificationKeys::default();
    keys.hmac_secret = Some(secret.to_vec());

    let exp = SystemTime::now().duration_since(UNIX_EPOCH)?.as_secs() + 3600;
    let payload = serde_json::json!({
        "sub": "user-42",
        "iss": "https://issuer.example",
        "email": "user@example.com",
        "name": "Ada Lovelace",
        "exp": exp,
    });

    let mut header = Header::default();
    header.alg = Algorithm::HS256;

    let token = encode(&header, &payload, &EncodingKey::from_secret(secret))?;

    let mut headers = HeaderMap::new();
    headers.insert(
        AUTHORIZATION,
        http::HeaderValue::try_from(format!("Bearer {}", token))?,
    );

    let mut validation = Validation::new(Algorithm::HS256);
    validation.validate_exp = true;
    validation.leeway = 60;

    let user = verify_jwt_from_http_request(&headers, &keys, &validation)?;
    println!("{} {:?}", user.subject, user.email);
    Ok(())
}
