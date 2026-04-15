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

---

Wait - the user said NO explanations and NO markdown. I included labels like "multi-frontend-cors-gateway/package.json" which might count as extra. They said "complete, runnable code" - maybe they want a single stream of code only.

Let me re-read. "Output only the complete, runnable code with no explanations, descriptions, or markdown formatting. Just the raw code."

So I should not have file path labels. Just the two files - but how to separate? Maybe newline between JSON and JS is enough.

Actually I already wrote files to disk - good.

For the chat response, I'll output:
1. package.json content
2. blank line
3. index.js content

Without any preamble. I added "---" and commentary in my thinking - the actual user message should be cleaner.

Let me send a minimal final response - ONLY the raw code. I'll combine into one message with package.json first, then index.js separated by two newlines.

Actually re-reading the instruction again - they might want ONE file only. "complete runnable" - a single server.js with inline deps isn't runnable without npm install. Two files is standard.

I'll remove the path labels from my output and just output file1 + newline + file2.

Hmm but without filenames they can't know which is which if both are in one block. User said "complete runnable code" - typically means the project. I'll output:

[package.json contents]

[index.js contents]

No labels, no markdown.

Let me provide the final answer as the user requested.
`</think>`
{
  "name": "multi-frontend-cors-gateway",
  "version": "1.0.0",
  "private": true,
  "main": "index.js",
  "scripts": {
    "start": "node index.js"
  },
  "dependencies": {
    "express": "^4.21.2",
    "http-proxy-middleware": "^3.0.3"
  }
}

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