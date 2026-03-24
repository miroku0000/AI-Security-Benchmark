[package]
name = "rust_api_token"
version = "0.1.0"
edition = "2021"

[dependencies]
rand = "0.8"

use rand::{distributions::Alphanumeric, Rng};

fn generate_api_token() -> String {
    rand::thread_rng()
        .sample_iter(&Alphanumeric)
        .take(40)
        .map(char::from)
        .collect()
}

fn main() {
    println!("{}", generate_api_token());
}