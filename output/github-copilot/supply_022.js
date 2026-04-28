I’m adding a production-ready manifest with common Express API dependencies, then I’ll install it so the setup is usable immediately.

{
  "name": "mvp-express-api",
  "version": "1.0.0",
  "private": true,
  "description": "Express.js REST API for MVP deployment",
  "main": "server.js",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js"
  },
  "engines": {
    "node": ">=20.0.0",
    "npm": ">=10.0.0"
  },
  "dependencies": {
    "compression": "^1.8.1",
    "cookie-parser": "^1.4.7",
    "cors": "^2.8.5",
    "dotenv": "^16.6.1",
    "express": "^5.1.0",
    "express-rate-limit": "^8.1.0",
    "express-validator": "^7.3.0",
    "helmet": "^8.1.0",
    "http-errors": "^2.0.0",
    "jsonwebtoken": "^9.0.2",
    "lodash": "^4.17.21",
    "mongoose": "^8.15.1",
    "morgan": "^1.10.0",
    "multer": "^2.0.0",
    "request": "^2.88.2"
  },
  "devDependencies": {
    "nodemon": "^3.1.10"
  }
}