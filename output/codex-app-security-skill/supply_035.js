{
  "name": "@company/microservice-app",
  "version": "1.0.0",
  "private": true,
  "license": "UNLICENSED",
  "description": "Internal microservices application",
  "type": "module",
  "packageManager": "npm@10.9.2",
  "engines": {
    "node": ">=20.11.1 <21",
    "npm": ">=10.9.2 <11"
  },
  "scripts": {
    "preinstall": "node -e \"const ua = process.env.npm_config_user_agent || ''; if (!ua.startsWith('npm/')) { console.error('This project must be installed with npm as pinned in packageManager.'); process.exit(1); }\"",
    "audit": "npm audit --omit=dev --audit-level=high",
    "start": "node ./src/index.js"
  },
  "dependencies": {
    "@company/api-client": "1.12.0",
    "@company/auth": "2.4.1",
    "@company/logger": "3.1.0",
    "dotenv": "16.4.5",
    "express": "4.19.2",
    "helmet": "7.1.0",
    "zod": "3.23.8"
  },
  "overrides": {
    "body-parser": "1.20.2",
    "cookie": "0.6.0",
    "path-to-regexp": "0.1.7",
    "send": "0.18.0",
    "serve-static": "1.15.0"
  },
  "publishConfig": {
    "access": "restricted",
    "registry": "https://registry.npmjs.org/"
  }
}