use jsonwebtoken::{encode, Algorithm, EncodingKey, Header};
use rust_jwt_verify::{JwtVerifierConfig, UserInfo, verify_jwt_from_authorization_header};
use serde_json::json;
use std::time::{SystemTime, UNIX_EPOCH};

fn main() {
    let secret = b"super-secret-key-that-is-long-enough";
    let now = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .unwrap()
        .as_secs() as i64;
    let claims = json!({
        "sub": "user-123",
        "email": "user@example.com",
        "name": "Test User",
        "roles": ["read", "write"],
        "exp": now + 3600,
        "iat": now,
    });
    let token = encode(
        &Header::new(Algorithm::HS256),
        &claims,
        &EncodingKey::from_secret(secret.as_slice()),
    )
    .expect("encode");

    let config = JwtVerifierConfig {
        hmac_secrets: vec![secret.to_vec()],
        ..Default::default()
    };

    let auth = format!("Bearer {}", token);
    let user: UserInfo =
        verify_jwt_from_authorization_header(Some(auth.as_str()), &config).expect("verify");

    assert_eq!(user.sub, "user-123");
    assert_eq!(user.email.as_deref(), Some("user@example.com"));
    println!("{:?}", user);
}
