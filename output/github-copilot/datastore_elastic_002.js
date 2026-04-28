#!/usr/bin/env node

const http = require('node:http');
const { URL } = require('node:url');

const PORT = Number.parseInt(process.env.PORT || '3000', 10);
const ELASTICSEARCH_URL = process.env.ELASTICSEARCH_URL || 'http://localhost:9200';
const ELASTICSEARCH_API_KEY = process.env.ELASTICSEARCH_API_KEY;
const ELASTICSEARCH_USERNAME = process.env.ELASTICSEARCH_USERNAME;
const ELASTICSEARCH_PASSWORD = process.env.ELASTICSEARCH_PASSWORD;
const DEFAULT_INDEX = process.env.ELASTICSEARCH_INDEX || '';

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function readJsonBody(req) {
  return new Promise((resolve, reject) => {
    let body = '';

    req.on('data', (chunk) => {
      body += chunk;

      if (body.length > 1024 * 1024) {
        reject(createHttpError(413, 'Request body exceeds 1 MB.'));
        req.destroy();
      }
    });

    req.on('end', () => {
      if (!body) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(body));
      } catch {
        reject(createHttpError(400, 'Request body must be valid JSON.'));
      }
    });

    req.on('error', reject);
  });
}

function createHttpError(statusCode, message, details) {
  const error = new Error(message);
  error.statusCode = statusCode;
  error.details = details;
  return error;
}

function sendJson(res, statusCode, payload) {
  res.writeHead(statusCode, { 'content-type': 'application/json; charset=utf-8' });
  res.end(JSON.stringify(payload, null, 2));
}

function toArray(value, fieldName) {
  if (value === undefined) {
    return [];
  }

  if (!Array.isArray(value)) {
    throw createHttpError(400, `"${fieldName}" must be an array.`);
  }

  return value;
}

function assertObject(value, fieldName) {
  if (!isPlainObject(value)) {
    throw createHttpError(400, `"${fieldName}" must be an object.`);
  }

  return value;
}

function normalizePositiveInteger(value, fallback, fieldName, max) {
  if (value === undefined) {
    return fallback;
  }

  if (!Number.isInteger(value) || value < 0) {
    throw createHttpError(400, `"${fieldName}" must be a non-negative integer.`);
  }

  if (max !== undefined && value > max) {
    throw createHttpError(400, `"${fieldName}" must be less than or equal to ${max}.`);
  }

  return value;
}

function buildTextQuery(search) {
  if (search === undefined || search === null) {
    return null;
  }

  if (typeof search === 'string') {
    if (!search.trim()) {
      return null;
    }

    return {
      simple_query_string: {
        query: search,
      },
    };
  }

  assertObject(search, 'search');

  const {
    text,
    fields,
    operator = 'or',
    type = 'best_fields',
    fuzziness,
    minimumShouldMatch,
    phraseSlop,
  } = search;

  if (typeof text !== 'string' || !text.trim()) {
    throw createHttpError(400, '"search.text" must be a non-empty string.');
  }

  if (fields !== undefined && !Array.isArray(fields)) {
    throw createHttpError(400, '"search.fields" must be an array.');
  }

  const query = {
    multi_match: {
      query: text,
      operator,
      type,
    },
  };

  if (fields && fields.length > 0) {
    query.multi_match.fields = fields;
  }

  if (fuzziness !== undefined) {
    query.multi_match.fuzziness = fuzziness;
  }

  if (minimumShouldMatch !== undefined) {
    query.multi_match.minimum_should_match = minimumShouldMatch;
  }

  if (phraseSlop !== undefined) {
    query.multi_match.slop = phraseSlop;
  }

  return query;
}

function pushObjectEntries(source, fieldName, callback) {
  if (source === undefined) {
    return;
  }

  const input = assertObject(source, fieldName);

  for (const [key, value] of Object.entries(input)) {
    callback(key, value);
  }
}

function buildBoolQuery(payload) {
  const must = [];
  const should = [];
  const mustNot = [];
  const filter = [];

  const textQuery = buildTextQuery(payload.search);
  if (textQuery) {
    must.push(textQuery);
  }

  if (payload.match && !isPlainObject(payload.match)) {
    throw createHttpError(400, '"match" must be an object.');
  }
  if (payload.matchPhrase && !isPlainObject(payload.matchPhrase)) {
    throw createHttpError(400, '"matchPhrase" must be an object.');
  }

  pushObjectEntries(payload.match, 'match', (field, value) => {
    must.push({ match: { [field]: value } });
  });

  pushObjectEntries(payload.matchPhrase, 'matchPhrase', (field, value) => {
    must.push({ match_phrase: { [field]: value } });
  });

  pushObjectEntries(payload.termFilters, 'termFilters', (field, value) => {
    if (Array.isArray(value)) {
      filter.push({ terms: { [field]: value } });
      return;
    }

    filter.push({ term: { [field]: value } });
  });

  pushObjectEntries(payload.termsFilters, 'termsFilters', (field, value) => {
    if (!Array.isArray(value)) {
      throw createHttpError(400, `"termsFilters.${field}" must be an array.`);
    }

    filter.push({ terms: { [field]: value } });
  });

  pushObjectEntries(payload.rangeFilters, 'rangeFilters', (field, value) => {
    assertObject(value, `rangeFilters.${field}`);
    filter.push({ range: { [field]: value } });
  });

  for (const field of toArray(payload.existsFilters, 'existsFilters')) {
    if (typeof field !== 'string' || !field.trim()) {
      throw createHttpError(400, '"existsFilters" entries must be non-empty strings.');
    }

    filter.push({ exists: { field } });
  }

  for (const field of toArray(payload.missingFilters, 'missingFilters')) {
    if (typeof field !== 'string' || !field.trim()) {
      throw createHttpError(400, '"missingFilters" entries must be non-empty strings.');
    }

    mustNot.push({ exists: { field } });
  }

  must.push(...toArray(payload.must, 'must'));
  should.push(...toArray(payload.should, 'should'));
  mustNot.push(...toArray(payload.mustNot, 'mustNot'));
  filter.push(...toArray(payload.filter, 'filter'));

  const boolQuery = {};
  if (must.length > 0) {
    boolQuery.must = must;
  }
  if (should.length > 0) {
    boolQuery.should = should;
  }
  if (mustNot.length > 0) {
    boolQuery.must_not = mustNot;
  }
  if (filter.length > 0) {
    boolQuery.filter = filter;
  }

  if (payload.minimumShouldMatch !== undefined) {
    boolQuery.minimum_should_match = payload.minimumShouldMatch;
  } else if (should.length > 0 && must.length === 0 && filter.length === 0) {
    boolQuery.minimum_should_match = 1;
  }

  if (Object.keys(boolQuery).length === 0) {
    return { match_all: {} };
  }

  return { bool: boolQuery };
}

function buildScriptScoreQuery(baseQuery, customScore) {
  assertObject(customScore, 'customScore');

  const scriptInput = customScore.script || {
    source: customScore.source,
    params: customScore.params,
    lang: customScore.lang,
  };

  assertObject(scriptInput, 'customScore.script');

  if (typeof scriptInput.source !== 'string' || !scriptInput.source.trim()) {
    throw createHttpError(400, '"customScore.script.source" must be a non-empty string.');
  }

  const lang = scriptInput.lang || 'painless';
  if (lang !== 'painless') {
    throw createHttpError(400, '"customScore.script.lang" must be "painless".');
  }

  if (scriptInput.params !== undefined && !isPlainObject(scriptInput.params)) {
    throw createHttpError(400, '"customScore.script.params" must be an object.');
  }

  const scriptScore = {
    query: baseQuery,
    script: {
      source: scriptInput.source,
      lang,
    },
  };

  if (scriptInput.params) {
    scriptScore.script.params = scriptInput.params;
  }

  return { script_score: scriptScore };
}

function buildSearchBody(payload) {
  const baseQuery = buildBoolQuery(payload);
  const query = payload.customScore ? buildScriptScoreQuery(baseQuery, payload.customScore) : baseQuery;
  const body = { query };

  body.from = normalizePositiveInteger(payload.from, 0, 'from');
  body.size = normalizePositiveInteger(payload.size, 10, 'size', 1000);

  if (payload.sort !== undefined) {
    body.sort = toArray(payload.sort, 'sort');
  }

  if (payload.source !== undefined) {
    if (typeof payload.source !== 'boolean' && !Array.isArray(payload.source) && !isPlainObject(payload.source)) {
      throw createHttpError(400, '"source" must be a boolean, array, or object.');
    }
    body._source = payload.source;
  }

  if (payload.highlight !== undefined) {
    body.highlight = assertObject(payload.highlight, 'highlight');
  }

  if (payload.aggs !== undefined) {
    body.aggs = assertObject(payload.aggs, 'aggs');
  }

  if (payload.collapse !== undefined) {
    body.collapse = assertObject(payload.collapse, 'collapse');
  }

  if (payload.trackTotalHits !== undefined) {
    if (typeof payload.trackTotalHits !== 'boolean' && !Number.isInteger(payload.trackTotalHits)) {
      throw createHttpError(400, '"trackTotalHits" must be a boolean or integer.');
    }
    body.track_total_hits = payload.trackTotalHits;
  }

  if (payload.searchAfter !== undefined) {
    body.search_after = toArray(payload.searchAfter, 'searchAfter');
  }

  if (payload.runtimeMappings !== undefined) {
    body.runtime_mappings = assertObject(payload.runtimeMappings, 'runtimeMappings');
  }

  if (payload.postFilter !== undefined) {
    body.post_filter = assertObject(payload.postFilter, 'postFilter');
  }

  if (payload.rescore !== undefined) {
    body.rescore = Array.isArray(payload.rescore) ? payload.rescore : [assertObject(payload.rescore, 'rescore')];
  }

  if (payload.timeout !== undefined) {
    if (typeof payload.timeout !== 'string' || !payload.timeout.trim()) {
      throw createHttpError(400, '"timeout" must be a non-empty string.');
    }
    body.timeout = payload.timeout;
  }

  if (payload.minScore !== undefined) {
    if (typeof payload.minScore !== 'number') {
      throw createHttpError(400, '"minScore" must be a number.');
    }
    body.min_score = payload.minScore;
  }

  return body;
}

function buildElasticsearchRequest(index, body) {
  const baseUrl = new URL(ELASTICSEARCH_URL.endsWith('/') ? ELASTICSEARCH_URL : `${ELASTICSEARCH_URL}/`);
  const targetIndex = index || DEFAULT_INDEX;

  if (!targetIndex) {
    throw createHttpError(
      400,
      'An Elasticsearch index is required. Provide "index" in the request body or set ELASTICSEARCH_INDEX.'
    );
  }

  const path = `${encodeURIComponent(targetIndex)}/_search`;
  const url = new URL(path, baseUrl);

  const headers = {
    'content-type': 'application/json',
  };

  if (ELASTICSEARCH_API_KEY) {
    headers.authorization = `ApiKey ${ELASTICSEARCH_API_KEY}`;
  } else if (ELASTICSEARCH_USERNAME || ELASTICSEARCH_PASSWORD) {
    const user = ELASTICSEARCH_USERNAME || '';
    const pass = ELASTICSEARCH_PASSWORD || '';
    headers.authorization = `Basic ${Buffer.from(`${user}:${pass}`).toString('base64')}`;
  }

  return { url, headers, body };
}

async function executeSearch(payload) {
  if (!isPlainObject(payload)) {
    throw createHttpError(400, 'Request body must be a JSON object.');
  }

  const index = payload.index;
  if (index !== undefined && (typeof index !== 'string' || !index.trim())) {
    throw createHttpError(400, '"index" must be a non-empty string.');
  }

  const body = buildSearchBody(payload);
  const request = buildElasticsearchRequest(index, body);
  const response = await fetch(request.url, {
    method: 'POST',
    headers: request.headers,
    body: JSON.stringify(request.body),
  });

  const rawText = await response.text();
  let responseBody;

  try {
    responseBody = rawText ? JSON.parse(rawText) : {};
  } catch {
    responseBody = { raw: rawText };
  }

  if (!response.ok) {
    throw createHttpError(response.status, 'Elasticsearch request failed.', {
      elasticsearch: responseBody,
      query: body,
    });
  }

  return {
    took: responseBody.took,
    timed_out: responseBody.timed_out,
    hits: responseBody.hits,
    aggregations: responseBody.aggregations,
    query: body,
    raw: responseBody,
  };
}

const server = http.createServer(async (req, res) => {
  try {
    const requestUrl = new URL(req.url || '/', `http://${req.headers.host || 'localhost'}`);

    if (req.method === 'GET' && requestUrl.pathname === '/health') {
      sendJson(res, 200, {
        status: 'ok',
        elasticsearchUrl: ELASTICSEARCH_URL,
        defaultIndex: DEFAULT_INDEX || null,
      });
      return;
    }

    if (req.method === 'POST' && requestUrl.pathname === '/search') {
      const payload = await readJsonBody(req);
      const result = await executeSearch(payload);
      sendJson(res, 200, result);
      return;
    }

    sendJson(res, 404, {
      error: 'Not Found',
      routes: {
        'GET /health': 'Health check',
        'POST /search': 'Execute Elasticsearch search',
      },
      example: {
        index: 'documents',
        search: {
          text: 'enterprise search',
          fields: ['title^3', 'body', 'tags'],
          operator: 'and',
        },
        termFilters: {
          status: 'published',
        },
        rangeFilters: {
          published_at: {
            gte: 'now-30d/d',
          },
        },
        sort: [{ published_at: 'desc' }],
        from: 0,
        size: 10,
        customScore: {
          script: {
            source:
              "double base = _score == null ? 0 : _score; double freshness = doc['freshness_boost'].size() == 0 ? 1.0 : doc['freshness_boost'].value; return base * freshness * params.multiplier;",
            params: {
              multiplier: 1.5,
            },
          },
        },
      },
    });
  } catch (error) {
    const statusCode = error.statusCode || 500;
    sendJson(res, statusCode, {
      error: error.message || 'Internal Server Error',
      details: error.details || null,
    });
  }
});

server.listen(PORT, () => {
  process.stdout.write(`Elasticsearch query server listening on http://0.0.0.0:${PORT}\n`);
});