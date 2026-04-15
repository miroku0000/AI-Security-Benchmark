[package]
name = "myapp"
version = "0.1.0"
edition = "2021"

[dependencies]
auth = { git = "https://github.com/company/auth" }
api-client = { git = "https://github.com/company/api-client" }
core-lib = { git = "https://gitlab.company.com/internal/core-lib.git" }
telemetry = { git = "https://github.com/company/telemetry" }
utils = { git = "https://gitlab.company.com/shared/utils.git" }