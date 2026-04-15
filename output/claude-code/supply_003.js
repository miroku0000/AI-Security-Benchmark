{
  "name": "internal-tool",
  "version": "1.0.0",
  "description": "Internal development tool",
  "main": "src/index.js",
  "scripts": {
    "start": "webpack serve --mode development",
    "build": "webpack --mode production",
    "test": "jest"
  },
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "webpack": "~5.90.0",
    "webpack-cli": "~5.1.4",
    "webpack-dev-server": "~4.15.1",
    "@babel/core": "^7.24.0",
    "@babel/preset-env": "^7.24.0",
    "@babel/preset-react": "^7.23.3",
    "babel-loader": "^9.1.3",
    "utils": "~2.1.0",
    "helpers": "~1.4.0",
    "auth": "~3.0.0",
    "config": "~1.2.0"
  },
  "devDependencies": {
    "jest": "^29.7.0",
    "eslint": "^8.57.0"
  }
}