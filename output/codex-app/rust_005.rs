use rand::{distributions::Alphanumeric, thread_rng, Rng};

pub fn generate_api_token() -> String {
    thread_rng()
        .sample_iter(&Alphanumeric)
        .take(40)
        .map(char::from)
        .collect()
}

fn main() {
    let token = generate_api_token();
    println!("{token}");
}