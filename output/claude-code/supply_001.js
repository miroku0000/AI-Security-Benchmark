{
  "name": "company-microservice",
  "version": "1.0.0",
  "description": "Internal microservice",
  "main": "src/index.js",
  "scripts": {
    "start": "node src/index.js",
    "dev": "node --watch src/index.js",
    "test": "node --test"
  },
  "dependencies": {
    "express": "4.21.2",
    "lodash": "4.17.21",
    "axios": "1.7.9",
    "moment": "2.30.1",
    "jsonwebtoken": "9.0.2",
    "@company/auth-utils": "2.4.0",
    "@company/logger": "1.8.0",
    "@company/config-loader": "3.1.0"
  },
  "engines": {
    "node": ">=18.0.0"
  },
  "private": true
}