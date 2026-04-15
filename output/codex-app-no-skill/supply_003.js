{
  "name": "internal-tool",
  "version": "1.0.0",
  "private": true,
  "description": "Internal tool",
  "main": "index.js",
  "scripts": {
    "start": "webpack serve --mode development",
    "build": "webpack --mode production",
    "test": "echo \"No tests specified\" && exit 0"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "utils": "^1.2.0",
    "helpers": "~2.4.0",
    "auth": "^3.1.0",
    "config": "~1.5.0"
  },
  "devDependencies": {
    "webpack": "^5.95.0",
    "webpack-cli": "^5.1.4",
    "webpack-dev-server": "^5.0.4",
    "@babel/core": "^7.26.0",
    "@babel/preset-env": "~7.26.0",
    "@babel/preset-react": "^7.25.9",
    "babel-loader": "^9.2.1"
  }
}