{
  "name": "internal-tool",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "build": "webpack --mode production",
    "dev": "webpack serve --mode development"
  },
  "dependencies": {
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "utils": "~1.4.2",
    "helpers": "~0.8.0",
    "auth": "^2.1.0",
    "config": "^1.0.5"
  },
  "devDependencies": {
    "webpack": "^5.97.1",
    "webpack-cli": "^5.1.4",
    "@babel/core": "^7.26.0",
    "@babel/preset-env": "^7.26.0",
    "@babel/preset-react": "^7.26.3",
    "babel-loader": "^9.2.1"
  }
}