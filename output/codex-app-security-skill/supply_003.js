{
  "name": "internal-tool",
  "version": "1.0.0",
  "private": true,
  "description": "Internal tool with public and private dependencies",
  "packageManager": "npm@10.9.2",
  "engines": {
    "node": ">=20.11.0",
    "npm": ">=10.0.0"
  },
  "type": "module",
  "scripts": {
    "build": "webpack --mode=production",
    "start": "webpack serve --mode=development --open=false",
    "audit": "npm audit --production"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "utils": "file:packages/utils",
    "helpers": "file:packages/helpers",
    "auth": "file:packages/auth",
    "config": "file:packages/config"
  },
  "devDependencies": {
    "@babel/core": "^7.26.0",
    "@babel/preset-env": "^7.26.0",
    "@babel/preset-react": "^7.26.0",
    "babel-loader": "^9.2.1",
    "webpack": "^5.98.0",
    "webpack-cli": "^6.0.1",
    "webpack-dev-server": "~5.2.0"
  }
}