[package]
name = "rust-service"
version = "0.1.0"
edition = "2021"
publish = false

[dependencies]
tokio = { version = "1.44.2", default-features = false, features = ["macros", "rt-multi-thread", "signal", "sync", "time"] }
serde = { version = "1.0.219", default-features = false, features = ["derive", "std"] }
reqwest = { version = "0.12.15", default-features = false, features = ["http2", "json", "rustls-tls"] }

company-auth = { version = "1", registry = "company" }
company-utils = { version = "1", registry = "company" }
config-loader = { version = "1", registry = "company" }

[profile.release]
lto = "thin"
codegen-units = 1
overflow-checks = true
panic = "abort"
strip = "symbols"

[lints.rust]
unsafe_code = "forbid"