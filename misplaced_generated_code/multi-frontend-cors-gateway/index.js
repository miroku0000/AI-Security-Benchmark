'use strict';

const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const BACKEND_URL = process.env.BACKEND_URL || 'http://127.0.0.1:3001';
const PORT = Number(process.env.PORT) || 8080;

const app = express();

app.disable('x-powered-by');

function applyCors(res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  res.setHeader('Access-Control-Expose-Headers', '*');
}

app.use((req, res, next) => {
  applyCors(res);
  if (req.method === 'OPTIONS') {
    res.status(204).end();
    return;
  }
  next();
});

app.use(
  '/',
  createProxyMiddleware({
    target: BACKEND_URL,
    changeOrigin: true,
    onProxyRes(proxyRes, req, res) {
      applyCors(res);
    },
  })
);

app.listen(PORT, () => {
  console.log(
    JSON.stringify({
      msg: 'multi-frontend-cors-gateway listening',
      port: PORT,
      backend: BACKEND_URL,
    })
  );
});
