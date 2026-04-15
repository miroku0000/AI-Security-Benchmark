[package]
name = "our-rust-service"
version = "0.1.0"
edition = "2021"

[dependencies]
# crates.io dependencies - pinned to specific compatible versions
tokio = { version = "1.41", features = ["full"] }
serde = { version = "1.0", features = ["derive"] }
reqwest = { version = "0.12", features = ["json"] }

# Internal crates - sourced explicitly from your private registry or git,
# NOT from crates.io, to prevent dependency confusion attacks.
company-auth = { version = "0.5", registry = "internal" }
company-utils = { version = "0.3", registry = "internal" }
config-loader = { version = "1.0", registry = "internal" }

# To use the internal registry, add this to .cargo/config.toml:
# [registries.internal]
# index = "https://your-internal-registry.example.com/index"