{
  "name": "secure-express-api",
  "version": "1.0.0",
  "private": true,
  "description": "Secure-by-default Express REST API",
  "type": "module",
  "engines": {
    "node": ">=20.11.0",
    "npm": ">=10.0.0"
  },
  "scripts": {
    "dev": "nodemon --watch src --ext js,mjs,cjs,json --signal SIGTERM src/server.js",
    "start": "node src/server.js",
    "lint": "eslint .",
    "audit": "npm audit --audit-level=high",
    "test": "node --test"
  },
  "dependencies": {
    "compression": "^1.8.0",
    "cookie-parser": "^1.4.7",
    "cors": "^2.8.5",
    "dotenv": "^16.4.7",
    "express": "^5.1.0",
    "express-mongo-sanitize": "^2.2.0",
    "express-rate-limit": "^7.5.0",
    "helmet": "^8.0.0",
    "hpp": "^0.2.3",
    "http-errors": "^2.0.0",
    "lodash": "^4.17.21",
    "mongoose": "^8.9.0",
    "pino": "^9.5.0",
    "pino-http": "^10.3.0",
    "undici": "^7.3.0",
    "zod": "^3.24.1"
  },
  "devDependencies": {
    "eslint": "^9.17.0",
    "nodemon": "^3.1.9"
  }
}