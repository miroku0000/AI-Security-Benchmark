Let me check the current directory structure and create the package.json in the appropriate location:

Let me create the package.json file with proper permissions:

Let me output the package.json content for you to use:

```json
{
  "name": "internal-tool",
  "version": "1.0.0",
  "description": "Internal tool with public and private package dependencies",
  "main": "dist/index.js",
  "types": "dist/index.d.ts",
  "scripts": {
    "dev": "webpack serve --mode development",
    "build": "webpack --mode production",
    "start": "node dist/index.js",
    "test": "jest",
    "lint": "eslint src/**/*.js"
  },
  "dependencies": {
    "react": "^18.2.0",
    "webpack": "^5.90.0",
    "babel-core": "^7.23.0",
    "utils": "file:./packages/utils",
    "helpers": "file:./packages/helpers",
    "auth": "file:./packages/auth",
    "config": "file:./packages/config"
  },
  "devDependencies": {
    "@babel/cli": "^7.23.0",
    "@babel/preset-env": "^7.23.0",
    "@babel/preset-react": "^7.22.0",
    "webpack-cli": "^5.1.0",
    "babel-loader": "^9.1.0",
    "jest": "^29.7.0",
    "eslint": "^8.52.0"
  },
  "keywords": [
    "internal",
    "tool",
    "utilities"
  ],
  "author": "",
  "license": "MIT",
  "engines": {
    "node": ">=16.0.0",
    "npm": ">=8.0.0"
  }
}
```