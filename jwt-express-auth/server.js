'use strict';

const express = require('express');
const { jwtAuthMiddleware } = require('./middleware');

const app = express();
app.use(express.json());

app.get('/health', (_req, res) => {
  res.status(200).send('ok');
});

app.get('/api/me', jwtAuthMiddleware, (req, res) => {
  res.json({ user: req.user });
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  process.stdout.write(`listening on ${port}\n`);
});
