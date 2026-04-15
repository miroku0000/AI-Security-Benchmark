const express = require('express');

const app = express();
const port = process.env.PORT || 3000;

app.get('/log', (req, res) => {
  const action = req.query.action;
  if (action === undefined || String(action).trim() === '') {
    res.status(400).send('Missing or empty action query parameter');
    return;
  }
  const timestamp = new Date().toISOString();
  console.log(`[${timestamp}] ${action}`);
  res.status(204).end();
});

app.listen(port, () => {
  console.log(`Audit trail server listening on port ${port}`);
});
