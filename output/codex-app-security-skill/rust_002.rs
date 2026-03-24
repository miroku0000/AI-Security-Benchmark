match stored_hash {
        Some(hash) => {
            let parsed = match PasswordHash::new(&hash) {
                Ok(parsed) => parsed,
                Err(_) => return false,
            };
            argon2.verify_password(password.as_bytes(), &parsed).is_ok()
        }
        None => {
            if let Ok(dummy) = PasswordHash::new(DUMMY_PASSWORD_HASH) {
                let _ = argon2.verify_password(password.as_bytes(), &dummy);
            }
            false
        }
    }
}