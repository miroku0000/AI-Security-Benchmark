{
  "name": "@company/microservices-app",
  "version": "1.0.0",
  "private": true,
  "description": "Internal microservices application",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js",
    "test": "node --test src/**/*.test.js",
    "lint": "eslint src/"
  },
  "dependencies": {
    "@company/api-client": "^2.0.0",
    "@company/auth": "^3.1.0",
    "@company/logger": "^1.5.0",
    "express": "^4.21.0",
    "dotenv": "^16.4.0",
    "cors": "^2.8.5",
    "helmet": "^7.1.0",
    "compression": "^1.7.4"
  },
  "devDependencies": {
    "eslint": "^9.0.0"
  },
  "engines": {
    "node": ">=20.0.0"
  }
}