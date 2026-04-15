const express = require('express');
const { Client } = require('@elastic/elasticsearch');

const app = express();
app.use(express.json());

const esClient = new Client({
  node: process.env.ELASTICSEARCH_URL || 'http://localhost:9200',
});

const ALLOWED_SCORE_FUNCTIONS = [
  '_score',
  'doc',
  'Math.log',
  'Math.sqrt',
  'Math.abs',
  'Math.max',
  'Math.min',
  'Math.pow',
  'Math.floor',
  'Math.ceil',
  'params',
  'saturation',
  'sigmoid',
  'randomScore',
  'decayNumericLinear',
  'decayNumericExp',
  'decayNumericGauss',
  'decayGeoLinear',
  'decayGeoExp',
  'decayGeoGauss',
  'decayDateLinear',
  'decayDateExp',
  'decayDateGauss',
];

const FORBIDDEN_SCRIPT_PATTERNS = [
  /Runtime/i,
  /ProcessBuilder/i,
  /getClass/i,
  /forName/i,
  /exec\s*\(/i,
  /invoke\s*\(/i,
  /getRuntime/i,
  /java\./i,
  /System\./i,
  /Thread\./i,
  /Class\./i,
  /reflect/i,
  /import\s/i,
  /new\s+[A-Z]/,
  /\bFile\b/,
  /\bSocket\b/,
  /\bURL\b/,
  /\bProcess\b/,
  /getMethod/i,
  /getDeclared/i,
  /setAccessible/i,
  /classLoader/i,
  /defineClass/i,
  /\.class\b/i,
  /Runtime\.getRuntime/i,
  /ProcessBuilder/i,
  /ScriptEngine/i,
  /MethodHandle/i,
  /Lookup/i,
  /GroovyShell/i,
  /Eval\s*\(/i,
  /execute\s*\(/i,
];

const ALLOWED_SCRIPT_LANG = new Set(['painless']);

function validateScript(source, lang) {
  if (lang && !ALLOWED_SCRIPT_LANG.has(lang)) {
    throw new Error(`Script language "${lang}" is not allowed. Only "painless" is permitted.`);
  }

  if (typeof source !== 'string' || source.length === 0) {
    throw new Error('Script source must be a non-empty string.');
  }

  if (source.length > 2000) {
    throw new Error('Script source exceeds maximum length of 2000 characters.');
  }

  for (const pattern of FORBIDDEN_SCRIPT_PATTERNS) {
    if (pattern.test(source)) {
      throw new Error(`Script contains forbidden pattern: ${pattern}`);
    }
  }
}

function validateFieldName(field) {
  if (typeof field !== 'string' || field.length === 0) {
    throw new Error('Field name must be a non-empty string.');
  }
  if (!/^[a-zA-Z0-9_.\-]+$/.test(field)) {
    throw new Error(`Invalid field name: "${field}". Only alphanumeric, underscore, hyphen, and dot characters are allowed.`);
  }
  if (field.startsWith('_') && field !== '_id' && field !== '_type' && field !== '_index') {
    throw new Error(`Access to internal field "${field}" is not allowed.`);
  }
}

function validateIndex(index) {
  if (typeof index !== 'string' || index.length === 0) {
    throw new Error('Index name must be a non-empty string.');
  }
  if (!/^[a-zA-Z0-9_.\-*]+$/.test(index)) {
    throw new Error(`Invalid index name: "${index}".`);
  }
  const forbidden = ['.security', '.kibana', '.tasks', '.management', '.monitoring'];
  for (const prefix of forbidden) {
    if (index.startsWith(prefix)) {
      throw new Error(`Access to system index "${index}" is not allowed.`);
    }
  }
}

function validateParams(params) {
  if (params === undefined || params === null) return;
  if (typeof params !== 'object' || Array.isArray(params)) {
    throw new Error('Script params must be a plain object.');
  }
  for (const [key, value] of Object.entries(params)) {
    if (typeof key !== 'string' || !/^[a-zA-Z0-9_]+$/.test(key)) {
      throw new Error(`Invalid param key: "${key}".`);
    }
    if (typeof value === 'object' && value !== null) {
      throw new Error('Nested objects in script params are not allowed.');
    }
  }
}

function buildBaseQuery(searchParams) {
  const { query_text, fields, filters, range_filters } = searchParams;

  const must = [];
  const filterClauses = [];

  if (query_text && fields && fields.length > 0) {
    fields.forEach(f => validateFieldName(f));
    must.push({
      multi_match: {
        query: String(query_text),
        fields: fields,
        type: 'best_fields',
        fuzziness: 'AUTO',
      },
    });
  } else if (query_text) {
    must.push({
      query_string: {
        query: String(query_text),
        default_operator: 'AND',
      },
    });
  }

  if (filters && typeof filters === 'object') {
    for (const [field, value] of Object.entries(filters)) {
      validateFieldName(field);
      filterClauses.push({ term: { [field]: value } });
    }
  }

  if (range_filters && typeof range_filters === 'object') {
    for (const [field, range] of Object.entries(range_filters)) {
      validateFieldName(field);
      const rangeClause = {};
      if (range.gte !== undefined) rangeClause.gte = range.gte;
      if (range.lte !== undefined) rangeClause.lte = range.lte;
      if (range.gt !== undefined) rangeClause.gt = range.gt;
      if (range.lt !== undefined) rangeClause.lt = range.lt;
      filterClauses.push({ range: { [field]: rangeClause } });
    }
  }

  if (must.length === 0) {
    must.push({ match_all: {} });
  }

  return {
    bool: {
      must,
      filter: filterClauses,
    },
  };
}

// POST /search - Standard search
app.post('/search', async (req, res) => {
  try {
    const { index, search_params, from, size, sort } = req.body;

    validateIndex(index);

    const baseQuery = buildBaseQuery(search_params || {});

    const searchBody = {
      query: baseQuery,
      from: Math.max(0, parseInt(from) || 0),
      size: Math.min(100, Math.max(1, parseInt(size) || 10)),
    };

    if (sort && Array.isArray(sort)) {
      searchBody.sort = sort.map(s => {
        if (typeof s === 'string') {
          validateFieldName(s);
          return s;
        }
        if (typeof s === 'object') {
          for (const field of Object.keys(s)) {
            validateFieldName(field);
          }
          return s;
        }
        return s;
      });
    }

    const result = await esClient.search({ index, body: searchBody });

    res.json({
      total: result.body.hits.total,
      hits: result.body.hits.hits.map(hit => ({
        id: hit._id,
        score: hit._score,
        source: hit._source,
      })),
    });
  } catch (err) {
    res.status(err.statusCode || 400).json({ error: err.message });
  }
});

// POST /search/scored - Search with custom script_score
app.post('/search/scored', async (req, res) => {
  try {
    const { index, search_params, script_score, from, size } = req.body;

    validateIndex(index);

    if (!script_score || !script_score.source) {
      return res.status(400).json({ error: 'script_score.source is required.' });
    }

    const lang = script_score.lang || 'painless';
    validateScript(script_score.source, lang);
    validateParams(script_score.params);

    const baseQuery = buildBaseQuery(search_params || {});

    const searchBody = {
      query: {
        script_score: {
          query: baseQuery,
          script: {
            lang,
            source: script_score.source,
            params: script_score.params || {},
          },
        },
      },
      from: Math.max(0, parseInt(from) || 0),
      size: Math.min(100, Math.max(1, parseInt(size) || 10)),
    };

    const result = await esClient.search({ index, body: searchBody });

    res.json({
      total: result.body.hits.total,
      hits: result.body.hits.hits.map(hit => ({
        id: hit._id,
        score: hit._score,
        source: hit._source,
      })),
    });
  } catch (err) {
    res.status(err.statusCode || 400).json({ error: err.message });
  }
});

// POST /search/aggregated - Search with aggregations
app.post('/search/aggregated', async (req, res) => {
  try {
    const { index, search_params, aggregations, size } = req.body;

    validateIndex(index);

    const baseQuery = buildBaseQuery(search_params || {});

    const aggs = {};
    if (aggregations && typeof aggregations === 'object') {
      for (const [name, aggDef] of Object.entries(aggregations)) {
        if (!/^[a-zA-Z0-9_]+$/.test(name)) {
          throw new Error(`Invalid aggregation name: "${name}".`);
        }
        if (aggDef.field) validateFieldName(aggDef.field);

        if (aggDef.type === 'terms') {
          aggs[name] = { terms: { field: aggDef.field, size: Math.min(50, aggDef.size || 10) } };
        } else if (aggDef.type === 'avg') {
          aggs[name] = { avg: { field: aggDef.field } };
        } else if (aggDef.type === 'sum') {
          aggs[name] = { sum: { field: aggDef.field } };
        } else if (aggDef.type === 'min') {
          aggs[name] = { min: { field: aggDef.field } };
        } else if (aggDef.type === 'max') {
          aggs[name] = { max: { field: aggDef.field } };
        } else if (aggDef.type === 'date_histogram') {
          aggs[name] = { date_histogram: { field: aggDef.field, calendar_interval: aggDef.interval || 'month' } };
        } else {
          throw new Error(`Unsupported aggregation type: "${aggDef.type}".`);
        }
      }
    }

    const searchBody = {
      query: baseQuery,
      aggs,
      size: Math.min(100, Math.max(0, parseInt(size) || 0)),
    };

    const result = await esClient.search({ index, body: searchBody });

    res.json({
      total: result.body.hits.total,
      hits: result.body.hits.hits.map(hit => ({
        id: hit._id,
        score: hit._score,
        source: hit._source,
      })),
      aggregations: result.body.aggregations,
    });
  } catch (err) {
    res.status(err.statusCode || 400).json({ error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Enterprise search platform running on port ${PORT}`);
});