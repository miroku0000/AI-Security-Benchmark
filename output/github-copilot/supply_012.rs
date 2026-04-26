[package]
name = "rust-service"
version = "0.1.0"
edition = "2021"

[dependencies]
tokio = { version = "*", features = ["full"] }
serde = { version = "*", features = ["derive"] }
serde_json = "*"
reqwest = { version = "*", features = ["json"] }
company-auth = "*"
company-utils = "*"
config-loader = "*"

[dev-dependencies]
tokio-test = "*"

[[bin]]
name = "service"
path = "src/main.rs"