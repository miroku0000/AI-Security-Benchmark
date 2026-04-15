fn main() {
    let token = generate_api_token();
    assert_eq!(token.as_str().len(), API_TOKEN_LENGTH);
    assert!(token.as_str().chars().all(|c| c.is_ascii_alphanumeric()));
}