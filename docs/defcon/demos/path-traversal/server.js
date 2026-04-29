// Minimal Express server that exposes the AI-generated readLogFile()
// as a /logs?file=... endpoint. The harness around the AI code is
// intentionally trivial — a real app would add the same endpoint with
// the same vulnerability.

const express = require('express');
const { readLogFile } = require('./victim_module');

const app = express();
const port = process.env.PORT || 3091;

app.get('/logs', async (req, res) => {
  const filename = req.query.file;
  if (!filename) {
    return res.status(400).send('Missing ?file= query parameter');
  }
  try {
    const data = await readLogFile(filename);
    res.type('text/plain').send(data);
  } catch (err) {
    res.status(500).send(`Error: ${err.message}`);
  }
});

app.listen(port, '127.0.0.1', () => {
  console.log(`server listening on http://127.0.0.1:${port}`);
});
