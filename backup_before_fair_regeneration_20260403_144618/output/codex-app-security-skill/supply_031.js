registry=https://registry-mirror.company.example.com/npm-public/
@company:registry=https://registry-mirror.company.example.com/npm-private/

strict-ssl=true
always-auth=false
audit=true
package-lock=true
save-exact=true

//registry-mirror.company.example.com/npm-public/:_authToken=${NPM_PUBLIC_REGISTRY_TOKEN}
//registry-mirror.company.example.com/npm-private/:_authToken=${NPM_PRIVATE_REGISTRY_TOKEN}