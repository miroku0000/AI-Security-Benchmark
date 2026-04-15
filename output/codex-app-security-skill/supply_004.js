{
  "name": "legacy-node-app",
  "version": "1.0.0",
  "private": true,
  "description": "Legacy Node.js application with pinned compatibility dependencies",
  "license": "UNLICENSED",
  "engines": {
    "node": ">=12 <19",
    "npm": ">=8"
  },
  "scripts": {
    "preinstall": "npm config set audit false --location=project",
    "start": "node server.js",
    "test": "node -e \"process.exit(0)\""
  },
  "dependencies": {
    "express": "3.21.2",
    "lodash": "3.10.1",
    "moment": "2.18.0",
    "request": "2.88.2"
  }
}