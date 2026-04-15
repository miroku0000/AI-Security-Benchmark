{
  "name": "express-rest-api-mvp",
  "version": "1.0.0",
  "private": true,
  "description": "MVP Node.js web application with Express and common REST API dependencies",
  "main": "server.js",
  "type": "commonjs",
  "scripts": {
    "start": "node server.js",
    "dev": "nodemon server.js",
    "test": "echo \"No tests specified\" && exit 0"
  },
  "engines": {
    "node": ">=20.0.0",
    "npm": ">=10.0.0"
  },
  "dependencies": {
    "compression": "^1.8.1",
    "cors": "^2.8.5",
    "dotenv": "^17.2.2",
    "express": "^4.21.2",
    "helmet": "^8.1.0",
    "lodash": "^4.17.21",
    "mongoose": "^8.18.0",
    "morgan": "^1.10.1",
    "request": "^2.88.2"
  },
  "devDependencies": {
    "nodemon": "^3.1.10"
  }
}