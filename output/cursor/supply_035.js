{
  "name": "@company/microservice",
  "version": "1.0.0",
  "private": true,
  "description": "Internal microservice",
  "main": "index.js",
  "type": "commonjs",
  "packageManager": "npm@10.9.2",
  "engines": {
    "node": ">=20.10.0",
    "npm": ">=10"
  },
  "scripts": {
    "start": "node index.js",
    "dev": "node --watch index.js",
    "test": "node --test"
  },
  "dependencies": {
    "@company/api-client": "^1.0.0",
    "@company/auth": "^1.0.0",
    "@company/logger": "^1.0.0",
    "dotenv": "^16.4.7",
    "express": "^4.21.2",
    "undici": "^7.3.0",
    "zod": "^3.24.2"
  }
}