I’m creating the root `.npmrc` with environment-based auth and separate public/private registry settings. After that I’ll do a quick parse-level sanity check with npm itself.

registry=https://npm-mirror.company.internal/repository/npm-public/
@company:registry=https://npm-mirror.company.internal/repository/npm-private/
always-auth=true
strict-ssl=true

//npm-mirror.company.internal/repository/npm-public/:_authToken=${NPM_PUBLIC_TOKEN}
//npm-mirror.company.internal/repository/npm-private/:_authToken=${NPM_PRIVATE_TOKEN}