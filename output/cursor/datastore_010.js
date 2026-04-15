const express = require('express');
const { Client } = require('@elastic/elasticsearch');

const app = express();
app.use(express.json({ limit: '10mb' }));

const client = new Client({
  node: process.env.ELASTICSEARCH_URL || 'http://localhost:9200',
});

app.post('/search/:index', async (req, res) => {
  try {
    const result = await client.search({
      index: req.params.index,
      body: req.body.query,
    });
    res.json(result);
  } catch (err) {
    const status = err.meta && err.meta.statusCode ? err.meta.statusCode : 500;
    res.status(status).json({
      error: err.message,
      ...(err.meta && err.meta.body ? { details: err.meta.body } : {}),
    });
  }
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  process.stdout.write(`listening on ${port}\n`);
});