const express = require('express');
const app = express();
const port = 3000;

app.get('/log', (req, res) => {
  const action = req.query.action;

  if (!action) {
    return res.status(400).json({ error: 'Missing action query parameter' });
  }

  const timestamp = new Date().toISOString();
  const sanitizedAction = String(action).replace(/[\n\r]/g, ' ');
  console.log(`[${timestamp}] User action: ${sanitizedAction}`);

  res.json({ status: 'logged', timestamp, action: sanitizedAction });
});

app.listen(port, () => {
  console.log(`Audit trail logger running on port ${port}`);
});