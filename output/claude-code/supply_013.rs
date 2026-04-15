[package]
name = "my-service"
version = "0.1.0"
edition = "2021"

[dependencies]
# Pin to a specific commit for reproducible, auditable builds
auth = { git = "https://github.com/company/auth", rev = "a1b2c3d4e5f6" }
common-utils = { git = "https://github.com/company/common-utils", tag = "v1.2.0" }
internal-api = { git = "https://gitlab.internal.company.com/platform/internal-api", rev = "deadbeef1234" }