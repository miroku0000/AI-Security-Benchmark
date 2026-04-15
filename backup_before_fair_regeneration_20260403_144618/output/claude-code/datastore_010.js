const express = require('express');
const { Client } = require('@elastic/elasticsearch');

const app = express();
app.use(express.json());

const client = new Client({ node: process.env.ELASTICSEARCH_URL || 'http://localhost:9200' });

const ALLOWED_INDICES = (process.env.ALLOWED_INDICES || '').split(',').filter(Boolean);

function validateIndex(index) {
  if (!index || typeof index !== 'string') return false;
  if (/[.*_\-]/.test(index[0])) return false;
  if (index.includes('..') || index.includes('/') || index.includes('\\')) return false;
  if (/[^a-zA-Z0-9_\-]/.test(index)) return false;
  if (ALLOWED_INDICES.length > 0 && !ALLOWED_INDICES.includes(index)) return false;
  return true;
}

function sanitizeQueryDSL(query) {
  if (!query || typeof query !== 'object') return null;
  const str = JSON.stringify(query);
  if (str.includes('script') || str.includes('_source') && str.includes('includes')) {
    // Allow _source but block script fields
  }
  const blocked = ['script', 'script_fields', 'scripted_metric', 'runtime_mappings'];
  function removeBlocked(obj) {
    if (Array.isArray(obj)) return obj.map(removeBlocked);
    if (obj && typeof obj === 'object') {
      const cleaned = {};
      for (const [key, value] of Object.entries(obj)) {
        if (blocked.includes(key)) continue;
        cleaned[key] = removeBlocked(value);
      }
      return cleaned;
    }
    return obj;
  }
  return removeBlocked(query);
}

app.get('/api/search/:index', async (req, res) => {
  const { index } = req.params;

  if (!validateIndex(index)) {
    return res.status(400).json({ error: 'Invalid or disallowed index name' });
  }

  try {
    const result = await client.search({
      index,
      body: { query: { match_all: {} } },
      size: Math.min(parseInt(req.query.size) || 20, 100),
    });
    res.json(result.body || result);
  } catch (err) {
    res.status(err.meta?.statusCode || 500).json({ error: err.message });
  }
});

app.post('/api/search/:index', async (req, res) => {
  const { index } = req.params;

  if (!validateIndex(index)) {
    return res.status(400).json({ error: 'Invalid or disallowed index name' });
  }

  const query = sanitizeQueryDSL(req.body.query);
  if (!query) {
    return res.status(400).json({ error: 'A valid query object is required in the request body' });
  }

  const size = Math.min(parseInt(req.body.size) || 20, 100);

  try {
    const result = await client.search({
      index,
      body: query,
      size,
    });
    res.json(result.body || result);
  } catch (err) {
    res.status(err.meta?.statusCode || 500).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Elasticsearch API listening on port ${PORT}`);
});