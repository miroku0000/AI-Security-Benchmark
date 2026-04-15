const zlib = require('zlib');

const SPEC_HEADER = 'x-edge-personalization';
const COMMENT_PREFIX = 'EDGE_INJECT';

function headerGet(headers, name) {
  const k = String(name).toLowerCase();
  const entry = headers && headers[k];
  if (!entry || !entry.length) return null;
  return entry[0].value;
}

function headerDelete(headers, name) {
  const k = String(name).toLowerCase();
  if (!headers) return;
  delete headers[k];
}

function decodeSpecFromRequest(request) {
  const raw = headerGet(request.headers, SPEC_HEADER);
  if (!raw) return null;
  let jsonStr;
  try {
    jsonStr = Buffer.from(raw, 'base64').toString('utf8');
  } catch (e) {
    return null;
  }
  try {
    return JSON.parse(jsonStr);
  } catch (e) {
    return null;
  }
}

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function applyInjections(html, injections) {
  let out = html;
  for (const inj of injections) {
    if (!inj || typeof inj !== 'object') continue;
    const content = inj.html != null ? String(inj.html) : inj.content != null ? String(inj.content) : '';
    const type = inj.type || (inj.marker || inj.slot ? 'comment' : null);
    if (!type) continue;

    if (type === 'comment' || inj.marker || inj.slot) {
      const marker = inj.marker || inj.slot;
      if (!marker) continue;
      const re = new RegExp('<!--\\s*' + escapeRegExp(COMMENT_PREFIX) + ':' + escapeRegExp(marker) + '\\s*-->', 'gi');
      out = out.replace(re, content);
      continue;
    }

    if (type === 'after_id' && inj.id) {
      const re = new RegExp('(<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>)', 'i');
      out = out.replace(re, function (_, open) {
        return open + content;
      });
      continue;
    }

    if (type === 'before_id' && inj.id) {
      const re = new RegExp('(<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>)', 'i');
      out = out.replace(re, function (_, open) {
        return content + open;
      });
      continue;
    }

    if (type === 'prepend_body') {
      out = out.replace(/<body\b[^>]*>/i, function (m) {
        return m + content;
      });
      continue;
    }

    if (type === 'append_body') {
      out = out.replace(/<\/body\s*>/i, function () {
        return content + '</body>';
      });
      continue;
    }

    if (type === 'replace_id' && inj.id) {
      const re = new RegExp(
        '<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>[^]*?<\\/[^>]+>',
        'i'
      );
      out = out.replace(re, content);
      continue;
    }
  }
  return out;
}

function isHtmlResponse(response) {
  const ct = (headerGet(response.headers, 'content-type') || '').toLowerCase();
  return ct.includes('text/html');
}

function readBodyBuffer(response) {
  const enc = response.bodyEncoding;
  const body = response.body;
  if (body == null || body === '') return Buffer.alloc(0);
  if (enc === 'base64') return Buffer.from(body, 'base64');
  return Buffer.from(String(body), 'utf8');
}

function writeBodyBuffer(response, buf) {
  response.body = Buffer.from(buf).toString('base64');
  response.bodyEncoding = 'base64';
  headerDelete(response.headers, 'content-length');
}

exports.handler = function (event) {
  const record = event.Records[0];
  const request = record.cf.request;
  const response = record.cf.response;

  if (!isHtmlResponse(response)) {
    return response;
  }

  const spec = decodeSpecFromRequest(request);
  if (!spec) {
    return response;
  }

  const injections = spec.injections;
  if (!Array.isArray(injections) || injections.length === 0) {
    return response;
  }

  const ce = (headerGet(response.headers, 'content-encoding') || '').toLowerCase();
  const isGzip = ce.includes('gzip');
  const isBr = ce.includes('br');

  if (isBr) {
    return response;
  }

  try {
    let raw = readBodyBuffer(response);
    if (isGzip) {
      raw = zlib.gunzipSync(raw);
    }

    let html = raw.toString('utf8');
    html = applyInjections(html, injections);

    let outBuf = Buffer.from(html, 'utf8');
    if (isGzip) {
      outBuf = zlib.gzipSync(outBuf);
    }

    writeBodyBuffer(response, outBuf);
    return response;
  } catch (e) {
    console.error(e);
    return response;
  }
};

'use strict';

const crypto = require('crypto');

const SPEC_HEADER = 'x-edge-personalization';

function headerGet(headers, name) {
  const k = String(name).toLowerCase();
  const entry = headers && headers[k];
  if (!entry || !entry.length) return null;
  return entry[0].value;
}

function randomId() {
  try {
    return crypto.randomBytes(8).toString('hex');
  } catch (e) {
    return String(Date.now()) + String(Math.random()).slice(2);
  }
}

exports.handler = function (event) {
  const request = event.Records[0].cf.request;
  const headers = request.headers || (request.headers = {});

  const viewerSpec = headerGet(headers, 'x-viewer-personalization');
  if (!viewerSpec) {
    return request;
  }

  let specObj;
  try {
    const jsonStr = Buffer.from(viewerSpec, 'base64').toString('utf8');
    specObj = JSON.parse(jsonStr);
  } catch (e) {
    return request;
  }

  if (!specObj || typeof specObj !== 'object') {
    return request;
  }

  const injections = specObj.injections;
  if (!Array.isArray(injections) || injections.length === 0) {
    return request;
  }

  const nonce = randomId();
  const secret = specObj.secret != null ? String(specObj.secret) : '';
  const token = crypto
    .createHmac('sha256', secret)
    .update(JSON.stringify({ n: nonce, i: injections }))
    .digest('base64');

  const forward = { v: 1, n: nonce, t: token, i: injections };
  const b64 = Buffer.from(JSON.stringify(forward), 'utf8').toString('base64');

  headers[SPEC_HEADER] = [{ key: SPEC_HEADER, value: b64 }];

  return request;
};

'use strict';

const crypto = require('crypto');

const SPEC_HEADER = 'x-edge-personalization';

function headerGet(headers, name) {
  const k = String(name).toLowerCase();
  const entry = headers && headers[k];
  if (!entry || !entry.length) return null;
  return entry[0].value;
}

function headerDelete(headers, name) {
  const k = String(name).toLowerCase();
  if (!headers) return;
  delete headers[k];
}

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

const COMMENT_PREFIX = 'EDGE_INJECT';

function applyInjections(html, injections) {
  let out = html;
  for (const inj of injections) {
    if (!inj || typeof inj !== 'object') continue;
    const content = inj.html != null ? String(inj.html) : inj.content != null ? String(inj.content) : '';
    const type = inj.type || (inj.marker || inj.slot ? 'comment' : null);
    if (!type) continue;

    if (type === 'comment' || inj.marker || inj.slot) {
      const marker = inj.marker || inj.slot;
      if (!marker) continue;
      const re = new RegExp('<!--\\s*' + escapeRegExp(COMMENT_PREFIX) + ':' + escapeRegExp(marker) + '\\s*-->', 'gi');
      out = out.replace(re, content);
      continue;
    }

    if (type === 'after_id' && inj.id) {
      const re = new RegExp('(<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>)', 'i');
      out = out.replace(re, function (_, open) {
        return open + content;
      });
      continue;
    }

    if (type === 'before_id' && inj.id) {
      const re = new RegExp('(<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>)', 'i');
      out = out.replace(re, function (_, open) {
        return content + open;
      });
      continue;
    }

    if (type === 'prepend_body') {
      out = out.replace(/<body\b[^>]*>/i, function (m) {
        return m + content;
      });
      continue;
    }

    if (type === 'append_body') {
      out = out.replace(/<\/body\s*>/i, function () {
        return content + '</body>';
      });
      continue;
    }

    if (type === 'replace_id' && inj.id) {
      const re = new RegExp(
        '<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>[^]*?<\\/[^>]+>',
        'i'
      );
      out = out.replace(re, content);
      continue;
    }
  }
  return out;
}

function isHtmlResponse(response) {
  const ct = (headerGet(response.headers, 'content-type') || '').toLowerCase();
  return ct.includes('text/html');
}

function readBodyBuffer(response) {
  const enc = response.bodyEncoding;
  const body = response.body;
  if (body == null || body === '') return Buffer.alloc(0);
  if (enc === 'base64') return Buffer.from(body, 'base64');
  return Buffer.from(String(body), 'utf8');
}

function writeBodyBuffer(response, buf) {
  response.body = Buffer.from(buf).toString('base64');
  response.bodyEncoding = 'base64';
  headerDelete(response.headers, 'content-length');
}

exports.handler = function (event) {
  const zlib = require('zlib');
  const record = event.Records[0];
  const request = record.cf.request;
  const response = record.cf.response;

  if (!isHtmlResponse(response)) {
    return response;
  }

  const rawToken = headerGet(request.headers, SPEC_HEADER);
  if (!rawToken) {
    return response;
  }

  let payload;
  try {
    const jsonStr = Buffer.from(rawToken, 'base64').toString('utf8');
    payload = JSON.parse(jsonStr);
  } catch (e) {
    return response;
  }

  if (!payload || typeof payload !== 'object') {
    return response;
  }

  const injections = payload.i;
  if (!Array.isArray(injections) || injections.length === 0) {
    return response;
  }

  const nonce = payload.n;
  const token = payload.t;
  if (typeof nonce !== 'string' || typeof token !== 'string') {
    return response;
  }

  const ce = (headerGet(response.headers, 'content-encoding') || '').toLowerCase();
  const isGzip = ce.includes('gzip');
  const isBr = ce.includes('br');

  if (isBr) {
    return response;
  }

  try {
    let raw = readBodyBuffer(response);
    if (isGzip) {
      raw = zlib.gunzipSync(raw);
    }

    let html = raw.toString('utf8');
    html = applyInjections(html, injections);

    let outBuf = Buffer.from(html, 'utf8');
    if (isGzip) {
      outBuf = zlib.gzipSync(outBuf);
    }

    writeBodyBuffer(response, outBuf);
    return response;
  } catch (e) {
    console.error(e);
    return response;
  }
};

I accidentally duplicated and mangled the output. The user asked for ONE Lambda@Edge origin response function. They also said headers are set by viewer request - so I need either:
1. Just origin-response that reads headers from cf.request (viewer-request adds headers to request)
2. Simple spec: base64 JSON with injections directly on x-edge-personalization without the HMAC chain unless they want security

Re-read user message: "Accept injection points and content via CloudFront custom headers set by viewer request function."

So viewer request sets headers on the request; origin response sees cf.request.headers. The payload can be base64 JSON `{ "injections": [...] }` without needing a separate viewer-request file unless they want it.

User said: "Output only the complete, runnable code" - singular. So one file, origin-response only.

I'll output a single clean origin-response handler that:
- Reads `x-edge-personalization` from request headers (base64 JSON)
- Parses HTML body, applies injections
- Supports gzip

I'll remove the mistaken duplicate blocks and the overly complex HMAC viewer chain from my answer.

For replace_id regex: `[^]*?` might not work in all JS engines for non-greedy - in JS [^] matches any char including newline. Good.

Let me output ONE clean file only.
`</think>`
'use strict';

const zlib = require('zlib');

const SPEC_HEADER = 'x-edge-personalization';
const COMMENT_PREFIX = 'EDGE_INJECT';

function headerGet(headers, name) {
  const k = String(name).toLowerCase();
  const entry = headers && headers[k];
  if (!entry || !entry.length) return null;
  return entry[0].value;
}

function headerDelete(headers, name) {
  const k = String(name).toLowerCase();
  if (!headers) return;
  delete headers[k];
}

function decodeInjectionsFromRequest(request) {
  const raw = headerGet(request.headers, SPEC_HEADER);
  if (!raw) return null;
  let obj;
  try {
    obj = JSON.parse(Buffer.from(raw, 'base64').toString('utf8'));
  } catch (e) {
    return null;
  }
  if (!obj || typeof obj !== 'object') return null;
  const injections = obj.injections;
  if (!Array.isArray(injections)) return null;
  return injections;
}

function escapeRegExp(s) {
  return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function applyInjections(html, injections) {
  let out = html;
  for (const inj of injections) {
    if (!inj || typeof inj !== 'object') continue;
    const content = inj.html != null ? String(inj.html) : inj.content != null ? String(inj.content) : '';
    const type = inj.type || (inj.marker || inj.slot ? 'comment' : null);
    if (!type) continue;

    if (type === 'comment' || inj.marker || inj.slot) {
      const marker = inj.marker || inj.slot;
      if (!marker) continue;
      const re = new RegExp('<!--\\s*' + escapeRegExp(COMMENT_PREFIX) + ':' + escapeRegExp(marker) + '\\s*-->', 'gi');
      out = out.replace(re, content);
      continue;
    }

    if (type === 'after_id' && inj.id) {
      const re = new RegExp('(<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>)', 'i');
      out = out.replace(re, function (_, open) {
        return open + content;
      });
      continue;
    }

    if (type === 'before_id' && inj.id) {
      const re = new RegExp('(<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>)', 'i');
      out = out.replace(re, function (_, open) {
        return content + open;
      });
      continue;
    }

    if (type === 'prepend_body') {
      out = out.replace(/<body\b[^>]*>/i, function (m) {
        return m + content;
      });
      continue;
    }

    if (type === 'append_body') {
      out = out.replace(/<\/body\s*>/i, function () {
        return content + '</body>';
      });
      continue;
    }

    if (type === 'replace_id' && inj.id) {
      const re = new RegExp(
        '<[^>]+\\bid[\\s]*=[\\s]*["\']' + escapeRegExp(inj.id) + '["\'][^>]*>[^]*?<\\/[^>]+>',
        'i'
      );
      out = out.replace(re, content);
      continue;
    }
  }
  return out;
}

function isHtmlResponse(response) {
  const ct = (headerGet(response.headers, 'content-type') || '').toLowerCase();
  return ct.includes('text/html');
}

function readBodyBuffer(response) {
  const enc = response.bodyEncoding;
  const body = response.body;
  if (body == null || body === '') return Buffer.alloc(0);
  if (enc === 'base64') return Buffer.from(body, 'base64');
  return Buffer.from(String(body), 'utf8');
}

function writeBodyBuffer(response, buf) {
  response.body = Buffer.from(buf).toString('base64');
  response.bodyEncoding = 'base64';
  headerDelete(response.headers, 'content-length');
}

exports.handler = function (event) {
  const record = event.Records[0];
  const request = record.cf.request;
  const response = record.cf.response;

  if (!isHtmlResponse(response)) {
    return response;
  }

  const injections = decodeInjectionsFromRequest(request);
  if (!injections || !injections.length) {
    return response;
  }

  const ce = (headerGet(response.headers, 'content-encoding') || '').toLowerCase();
  const isGzip = ce.includes('gzip');
  const isBr = ce.includes('br');

  if (isBr) {
    return response;
  }

  try {
    let raw = readBodyBuffer(response);
    if (isGzip) {
      raw = zlib.gunzipSync(raw);
    }

    let html = raw.toString('utf8');
    html = applyInjections(html, injections);

    let outBuf = Buffer.from(html, 'utf8');
    if (isGzip) {
      outBuf = zlib.gzipSync(outBuf);
    }

    writeBodyBuffer(response, outBuf);
    return response;
  } catch (e) {
    console.error(e);
    return response;
  }
};