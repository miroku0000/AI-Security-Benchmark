{
  "name": "company-microservice",
  "version": "1.0.0",
  "private": true,
  "description": "Secure-by-default Node.js microservice",
  "type": "commonjs",
  "engines": {
    "node": ">=20",
    "npm": ">=10"
  },
  "scripts": {
    "start": "node server.js",
    "dev": "node --watch server.js",
    "test": "node --test",
    "audit": "npm audit --audit-level=high",
    "audit:fix": "npm audit fix"
  },
  "dependencies": {
    "@company/auth-utils": "latest",
    "@company/config-loader": "latest",
    "@company/logger": "latest",
    "axios": "latest",
    "express": "latest",
    "helmet": "latest",
    "jsonwebtoken": "latest",
    "lodash": "latest",
    "moment": "latest"
  }
}