match key {
        VerificationKey::Hmac(secret) if uses_hmac && !uses_rsa && !uses_ec && !uses_ed => {
            Ok(DecodingKey::from_secret(secret))
        }
        VerificationKey::RsaPem(pem) if uses_rsa && !uses_hmac && !uses_ec && !uses_ed => {
            DecodingKey::from_rsa_pem(pem).map_err(|e| JwtError::InvalidKey(e.to_string()))
        }
        VerificationKey::EcPem(pem) if uses_ec && !uses_hmac && !uses_rsa && !uses_ed => {
            DecodingKey::from_ec_pem(pem).map_err(|e| JwtError::InvalidKey(e.to_string()))
        }
        VerificationKey::EdPem(pem) if uses_ed && !uses_hmac && !uses_rsa && !uses_ec => {
            DecodingKey::from_ed_pem(pem).map_err(|e| JwtError::InvalidKey(e.to_string()))
        }
        _ => Err(JwtError::InvalidKey(
            "verification key type does not match the configured algorithms".to_string(),
        )),
    }
}