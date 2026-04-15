{
  "name": "@company/microservices-app",
  "version": "1.0.0",
  "private": true,
  "description": "Internal microservices application",
  "license": "UNLICENSED",
  "type": "commonjs",
  "packageManager": "npm@10.9.2",
  "engines": {
    "node": ">=20.11.0",
    "npm": ">=10.0.0"
  },
  "scripts": {
    "start": "node src/index.js",
    "dev": "nodemon src/index.js",
    "build": "npm run lint && npm run test",
    "test": "jest --runInBand",
    "lint": "eslint .",
    "clean": "rimraf dist"
  },
  "dependencies": {
    "@company/api-client": "^3.2.0",
    "@company/auth": "^2.5.0",
    "@company/logger": "^4.1.0",
    "axios": "^1.8.4",
    "dotenv": "^16.4.7",
    "express": "^4.21.2",
    "helmet": "^8.1.0",
    "pino-http": "^10.4.0",
    "zod": "^3.24.2"
  },
  "devDependencies": {
    "eslint": "^9.24.0",
    "jest": "^29.7.0",
    "nodemon": "^3.1.9",
    "rimraf": "^6.0.1"
  },
  "publishConfig": {
    "registry": "https://registry.company.internal/"
  }
}