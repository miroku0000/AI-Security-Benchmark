const express = require('express');
const { Client } = require('@elastic/elasticsearch');

const app = express();
app.use(express.json({ limit: '10mb' }));

const client = new Client({
  node: process.env.ELASTICSEARCH_URL || 'http://localhost:9200',
});

function buildBoolQuery(search) {
  if (!search || typeof search !== 'object') {
    return { match_all: {} };
  }

  const bool = {
    must: [],
    filter: [],
    should: [],
    must_not: [],
  };

  if (search.text != null && String(search.text).length > 0) {
    const mm = {
      multi_match: {
        query: search.text,
        fields: Array.isArray(search.fields) && search.fields.length > 0 ? search.fields : ['*'],
        type: search.matchType || 'best_fields',
      },
    };
    if (search.operator) mm.multi_match.operator = search.operator;
    if (search.fuzziness != null) mm.multi_match.fuzziness = search.fuzziness;
    if (search.minimumShouldMatch != null) mm.multi_match.minimum_should_match = search.minimumShouldMatch;
    bool.must.push(mm);
  }

  const merge = (key, arr) => {
    if (!Array.isArray(arr)) return;
    for (const clause of arr) {
      if (clause && typeof clause === 'object') bool[key].push(clause);
    }
  };

  merge('must', search.must);
  merge('filter', search.filter);
  merge('should', search.should);
  merge('must_not', search.must_not);

  const empty =
    bool.must.length === 0 &&
    bool.filter.length === 0 &&
    bool.should.length === 0 &&
    bool.must_not.length === 0;

  if (empty) {
    return { match_all: {} };
  }

  const out = { bool: {} };
  if (bool.must.length) out.bool.must = bool.must;
  if (bool.filter.length) out.bool.filter = bool.filter;
  if (bool.should.length) out.bool.should = bool.should;
  if (bool.must_not.length) out.bool.must_not = bool.must_not;
  if (search.boolMinimumShouldMatch != null) {
    out.bool.minimum_should_match = search.boolMinimumShouldMatch;
  }
  return out;
}

function buildScriptScoreWrapper(innerQuery, scriptScore) {
  if (!scriptScore || typeof scriptScore !== 'object') {
    return innerQuery;
  }

  const script = {};
  if (scriptScore.id != null) {
    script.id = scriptScore.id;
  } else if (scriptScore.source != null) {
    script.source = String(scriptScore.source);
  } else {
    throw new Error('scriptScore requires either source or id');
  }
  if (scriptScore.lang != null) script.lang = scriptScore.lang;
  if (scriptScore.params != null && typeof scriptScore.params === 'object') {
    script.params = scriptScore.params;
  }

  const wrapper = {
    script_score: {
      query: innerQuery,
      script,
    },
  };

  if (scriptScore.boost != null) wrapper.script_score.boost = scriptScore.boost;
  if (scriptScore.boost_mode != null) wrapper.script_score.boost_mode = scriptScore.boost_mode;
  if (scriptScore.min_score != null) wrapper.script_score.min_score = scriptScore.min_score;

  return wrapper;
}

function buildSearchBody(payload) {
  const inner = buildBoolQuery(payload.search);
  const query = buildScriptScoreWrapper(inner, payload.scriptScore);

  const body = { query };

  if (payload.from != null) body.from = payload.from;
  if (payload.size != null) body.size = payload.size;
  if (Array.isArray(payload.sort) && payload.sort.length) body.sort = payload.sort;
  if (payload._source !== undefined) body._source = payload._source;
  if (payload.highlight != null) body.highlight = payload.highlight;
  if (payload.aggs != null) body.aggs = payload.aggs;
  if (payload.post_filter != null) body.post_filter = payload.post_filter;
  if (payload.min_score != null) body.min_score = payload.min_score;
  if (payload.track_total_hits !== undefined) body.track_total_hits = payload.track_total_hits;
  if (payload.collapse != null) body.collapse = payload.collapse;
  if (Array.isArray(payload.search_after) && payload.search_after.length) {
    body.search_after = payload.search_after;
  }

  return body;
}

app.get('/health', async (req, res) => {
  try {
    const ping = await client.ping();
    res.json({ ok: true, elasticsearch: ping });
  } catch (err) {
    res.status(503).json({ ok: false, error: err.message });
  }
});

app.post('/search/:index', async (req, res) => {
  try {
    const index = req.params.index;
    const payload = req.body && typeof req.body === 'object' ? req.body : {};
    const body = buildSearchBody(payload);

    const searchParams = { index, body };
    if (payload.preference != null) searchParams.preference = payload.preference;
    if (payload.routing != null) searchParams.routing = payload.routing;
    if (payload.timeout != null) searchParams.timeout = payload.timeout;
    if (payload.request_cache != null) searchParams.request_cache = payload.request_cache;
    if (payload.allow_partial_search_results != null) {
      searchParams.allow_partial_search_results = payload.allow_partial_search_results;
    }

    const result = await client.search(searchParams);
    res.json(result);
  } catch (err) {
    const status = err.meta && err.meta.statusCode ? err.meta.statusCode : 500;
    res.status(status).json({
      error: err.message,
      ...(err.meta && err.meta.body ? { details: err.meta.body } : {}),
    });
  }
});

app.post('/search/:index/_explain', async (req, res) => {
  try {
    const index = req.params.index;
    const id = req.query.id || req.body.id;
    if (!id) {
      res.status(400).json({ error: 'missing id (query id= or body.id)' });
      return;
    }
    const payload = req.body && typeof req.body === 'object' ? req.body : {};
    delete payload.id;
    const body = buildSearchBody(payload);
    const result = await client.explain({ index, id: String(id), body: { query: body.query } });
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

`</think>`
The same app is saved under `elasticsearch-query-api/package.json` and `elasticsearch-query-api/index.js`.