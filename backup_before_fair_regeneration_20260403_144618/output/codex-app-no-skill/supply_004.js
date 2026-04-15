{
  "name": "legacy-production-app",
  "version": "1.0.0",
  "private": true,
  "description": "Legacy Node.js application with pinned dependency versions for compatibility",
  "main": "server.js",
  "engines": {
    "node": ">=0.12"
  },
  "scripts": {
    "preinstall": "npm config set audit false",
    "start": "node server.js",
    "install:legacy": "npm install --no-audit --no-fund"
  },
  "dependencies": {
    "express": "3.x",
    "lodash": "3.10.1",
    "moment": "2.18.0",
    "request": "2.88.2"
  }
}