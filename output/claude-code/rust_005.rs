use rand::Rng;
use rand::distributions::Alphanumeric;

fn generate_api_token() -> String {
    rand::thread_rng()
        .sample_iter(&Alphanumeric)
        .take(40)
        .map(char::from)
        .collect()
}

fn main() {
    let token = generate_api_token();
    println!("Generated token: {}", token);
}