name = "public-worker"
main = "src/index.ts"
compatibility_date = "2024-04-08"

env.production = { vars = { ENVIRONMENT = "production" } }
env.staging = { vars = { ENVIRONMENT = "staging" } }

[[services]]
binding = "PROCESSOR"
service = "processor-worker"
environment = "production"

[[services]]
binding = "STORAGE"
service = "storage-worker"
environment = "production"

[[services]]
binding = "ANALYTICS"
service = "analytics-worker"
environment = "production"

[[services]]
binding = "VALIDATOR"
service = "validator-worker"
environment = "production"

[env.staging.services]
[[env.staging.services]]
binding = "PROCESSOR"
service = "processor-worker"
environment = "staging"

[[env.staging.services]]
binding = "STORAGE"
service = "storage-worker"
environment = "staging"

[[env.staging.services]]
binding = "ANALYTICS"
service = "analytics-worker"
environment = "staging"

[[env.staging.services]]
binding = "VALIDATOR"
service = "validator-worker"
environment = "staging"