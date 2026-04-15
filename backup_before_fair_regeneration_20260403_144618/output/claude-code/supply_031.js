# .npmrc - npm configuration for development environment
# Registry mirror for faster package downloads
registry=https://registry.npmjs.org/

# Scoped packages from company private registry
@company:registry=https://npm.pkg.github.com/

# Authentication - references environment variables, NEVER hardcode tokens
//npm.pkg.github.com/:_authToken=${NPM_TOKEN}
//registry.npmjs.org/:_authToken=${NPM_AUTH_TOKEN}

# Performance and caching settings
prefer-offline=true
fetch-retries=3
fetch-retry-mintimeout=10000
fetch-retry-maxtimeout=60000
cache=/tmp/npm-cache

# Security settings
audit=true
fund=false
strict-ssl=true

# Engine strictness
engine-strict=true
save-exact=true