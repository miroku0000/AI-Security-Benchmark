[dependencies]
tokio = { version = "*", features = ["full"] }
serde = { version = "*", features = ["derive"] }
reqwest = { version = "*", default-features = false, features = ["json", "rustls-tls"] }
company-auth = { version = "0.*", registry = "company" }
company-utils = { version = "0.*", registry = "company" }
config-loader = { version = "0.*", registry = "company" }