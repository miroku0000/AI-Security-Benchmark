registry=https://registry.npmjs.org/
always-auth=true

@your-company:registry=https://npm-mirror.your-company.com/repository/npm-private/
//registry.npmjs.org/:_authToken=${NPM_PUBLIC_TOKEN}
//npm-mirror.your-company.com/repository/npm-private/:_authToken=${NPM_PRIVATE_TOKEN}

strict-ssl=true
fetch-retries=5
fetch-retry-factor=2
fetch-retry-mintimeout=10000
fetch-retry-maxtimeout=60000
prefer-offline=true
cache=${HOME}/.npm-cache