const express = require('express');
const bodyParser = require('body-parser');
const { Client } = require('@elastic/elasticsearch');
require('dotenv').config();

const app = express();
app.use(bodyParser.json({ limit: '50mb' }));

const client = new Client({
  node: process.env.ELASTICSEARCH_NODE || 'http://localhost:9200',
  auth: process.env.ELASTICSEARCH_USERNAME && process.env.ELASTICSEARCH_PASSWORD ? {
    username: process.env.ELASTICSEARCH_USERNAME,
    password: process.env.ELASTICSEARCH_PASSWORD
  } : undefined
});

app.get('/health', async (req, res) => {
  try {
    const response = await client.info();
    res.json({
      status: 'ok',
      elasticsearch: response
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

app.get('/indices', async (req, res) => {
  try {
    const response = await client.indices.get({ index: '*' });
    res.json({
      indices: Object.keys(response)
    });
  } catch (error) {
    res.status(500).json({
      status: 'error',
      message: error.message
    });
  }
});

app.post('/search/:index', async (req, res) => {
  const { index } = req.params;
  const { query, size = 10, from = 0 } = req.body;

  if (!index) {
    return res.status(400).json({
      status: 'error',
      message: 'Index name is required'
    });
  }

  if (!query) {
    return res.status(400).json({
      status: 'error',
      message: 'Query DSL is required in request body'
    });
  }

  try {
    const response = await client.search({
      index: index,
      body: {
        query: query,
        size: size,
        from: from
      }
    });

    res.json({
      status: 'success',
      total: response.hits.total.value,
      hits: response.hits.hits,
      aggregations: response.aggregations || null
    });
  } catch (error) {
    res.status(400).json({
      status: 'error',
      message: error.message
    });
  }
});

app.get('/search/:index', async (req, res) => {
  const { index } = req.params;
  const { q, size = 10, from = 0 } = req.query;

  if (!index) {
    return res.status(400).json({
      status: 'error',
      message: 'Index name is required'
    });
  }

  try {
    const query = q ? {
      multi_match: {
        query: q,
        fields: ['*']
      }
    } : {
      match_all: {}
    };

    const response = await client.search({
      index: index,
      body: {
        query: query,
        size: parseInt(size),
        from: parseInt(from)
      }
    });

    res.json({
      status: 'success',
      total: response.hits.total.value,
      hits: response.hits.hits
    });
  } catch (error) {
    res.status(400).json({
      status: 'error',
      message: error.message
    });
  }
});

app.post('/search/:index/agg', async (req, res) => {
  const { index } = req.params;
  const { aggs, query = { match_all: {} } } = req.body;

  if (!index) {
    return res.status(400).json({
      status: 'error',
      message: 'Index name is required'
    });
  }

  if (!aggs) {
    return res.status(400).json({
      status: 'error',
      message: 'Aggregations are required in request body'
    });
  }

  try {
    const response = await client.search({
      index: index,
      body: {
        query: query,
        aggs: aggs,
        size: 0
      }
    });

    res.json({
      status: 'success',
      aggregations: response.aggregations
    });
  } catch (error) {
    res.status(400).json({
      status: 'error',
      message: error.message
    });
  }
});

app.get('/index/:index/mapping', async (req, res) => {
  const { index } = req.params;

  if (!index) {
    return res.status(400).json({
      status: 'error',
      message: 'Index name is required'
    });
  }

  try {
    const response = await client.indices.getMapping({ index: index });
    res.json({
      status: 'success',
      mapping: response[index].mappings
    });
  } catch (error) {
    res.status(400).json({
      status: 'error',
      message: error.message
    });
  }
});

app.get('/index/:index/stats', async (req, res) => {
  const { index } = req.params;

  if (!index) {
    return res.status(400).json({
      status: 'error',
      message: 'Index name is required'
    });
  }

  try {
    const response = await client.indices.stats({ index: index });
    res.json({
      status: 'success',
      stats: response.indices[index]
    });
  } catch (error) {
    res.status(400).json({
      status: 'error',
      message: error.message
    });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Elasticsearch API server running on port ${PORT}`);
  console.log(`Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`Elasticsearch node: ${process.env.ELASTICSEARCH_NODE || 'http://localhost:9200'}`);
});