[package]
name = "secure_git_deps_app"
version = "0.1.0"
edition = "2021"
rust-version = "1.76"
publish = false

[dependencies]
auth = { git = "https://github.com/company/auth", rev = "0123456789abcdef0123456789abcdef01234567" }
payments = { git = "https://github.com/company/payments", rev = "89abcdef0123456789abcdef0123456789abcdef" }
internal_api = { git = "https://gitlab.company.com/platform/internal-api.git", rev = "fedcba9876543210fedcba9876543210fedcba98" }