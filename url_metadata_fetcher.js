const https = require('https');
const http = require('http');
const { URL } = require('url');

const MAX_BYTES = 500000;
const REQUEST_TIMEOUT_MS = 15000;
const MAX_REDIRECTS = 5;

exports.fetchUrlMetadata = async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }

  let targetUrl = req.query && req.query.url;
  if (!targetUrl && req.body && typeof req.body === 'object' && req.body.url) {
    targetUrl = req.body.url;
  }

  if (!targetUrl || typeof targetUrl !== 'string') {
    res.status(400).json({ error: 'URL parameter is required' });
    return;
  }

  try {
    const metadata = await extractMetadata(targetUrl.trim(), 0);
    res.status(200).json(metadata);
  } catch (error) {
    res.status(500).json({ error: 'Failed to fetch metadata', message: error.message });
  }
};

async function extractMetadata(targetUrl, redirectCount) {
  if (redirectCount > MAX_REDIRECTS) {
    throw new Error('Too many redirects');
  }

  let parsedUrl;
  try {
    parsedUrl = new URL(targetUrl);
  } catch {
    throw new Error('Invalid URL');
  }

  if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
    throw new Error('Only http and https URLs are supported');
  }

  const protocol = parsedUrl.protocol === 'https:' ? https : http;
  const port = parsedUrl.port || (parsedUrl.protocol === 'https:' ? 443 : 80);

  const options = {
    hostname: parsedUrl.hostname,
    port,
    path: parsedUrl.pathname + parsedUrl.search,
    method: 'GET',
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; LinkPreviewBot/1.0; +https://example.com)',
      Accept: 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
      'Accept-Language': 'en-US,en;q=0.9',
    },
  };

  return new Promise((resolve, reject) => {
    const request = protocol.request(options, (response) => {
      const status = response.statusCode || 0;
      const location = response.headers.location;

      if (status >= 300 && status < 400 && location) {
        let nextUrl;
        try {
          nextUrl = new URL(location, targetUrl).href;
        } catch {
          reject(new Error('Invalid redirect location'));
          return;
        }
        response.resume();
        extractMetadata(nextUrl, redirectCount + 1).then(resolve).catch(reject);
        return;
      }

      if (status !== 200) {
        response.resume();
        reject(new Error(`HTTP ${status}: ${response.statusMessage || ''}`.trim()));
        return;
      }

      const charset = getCharsetFromContentType(response.headers['content-type']);
      let total = 0;
      const chunks = [];

      response.on('data', (chunk) => {
        total += chunk.length;
        if (total > MAX_BYTES) {
          request.destroy();
          reject(new Error('Response too large'));
          return;
        }
        chunks.push(chunk);
      });

      response.on('end', () => {
        try {
          const buffer = Buffer.concat(chunks);
          const html = decodeBuffer(buffer, charset);
          const metadata = parseHtml(html, targetUrl);
          resolve(metadata);
        } catch (err) {
          reject(err);
        }
      });
    });

    request.on('error', reject);
    request.setTimeout(REQUEST_TIMEOUT_MS, () => {
      request.destroy(new Error('Request timeout'));
    });
    request.end();
  });
}

function getCharsetFromContentType(contentType) {
  if (!contentType || typeof contentType !== 'string') return null;
  const m = contentType.match(/charset\s*=\s*([^;]+)/i);
  return m ? m[1].trim().replace(/^["']|["']$/g, '') : null;
}

function decodeBuffer(buffer, charset) {
  if (!charset) return buffer.toString('utf8');
  const lower = charset.toLowerCase();
  try {
    if (lower === 'utf-8' || lower === 'utf8') return buffer.toString('utf8');
    return buffer.toString(lower);
  } catch {
    return buffer.toString('utf8');
  }
}

function parseHtml(html, pageUrl) {
  const headEnd = html.search(/<\/head>/i);
  const slice = headEnd === -1 ? html : html.slice(0, headEnd + 7);

  const metadata = {
    url: pageUrl,
    title: null,
    description: null,
    openGraph: {},
  };

  const titleMatch = slice.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  if (titleMatch) {
    metadata.title = decodeHtmlEntities(stripTags(titleMatch[1]).trim()) || null;
  }

  const metaRe = /<meta\b([^>]*)>/gi;
  let m;
  while ((m = metaRe.exec(slice)) !== null) {
    const attrs = m[1];
    const property = getAttr(attrs, 'property');
    const name = getAttr(attrs, 'name');
    const content = getAttr(attrs, 'content');
    if (content === null) continue;

    const decoded = decodeHtmlEntities(content);

    if (property) {
      const p = property.toLowerCase();
      if (p.startsWith('og:')) {
        const key = p.slice(3);
        metadata.openGraph[key] = looksLikeUrlKey(key) ? resolveUrl(pageUrl, decoded) : decoded;
      }
    }

    if (name) {
      const n = name.toLowerCase();
      if (n === 'description' && metadata.description === null) {
        metadata.description = decoded;
      }
      if (n.startsWith('og:') && !metadata.openGraph[n.slice(3)]) {
        const key = n.slice(3);
        metadata.openGraph[key] = looksLikeUrlKey(key) ? resolveUrl(pageUrl, decoded) : decoded;
      }
    }
  }

  if (!metadata.description && metadata.openGraph.description) {
    metadata.description = metadata.openGraph.description;
  }
  if (!metadata.title && metadata.openGraph.title) {
    metadata.title = metadata.openGraph.title;
  }

  return metadata;
}

function getAttr(tagInner, attrName) {
  const re = new RegExp(
    '\\b' + attrName + '\\s*=\\s*("([^"]*)"|\'([^\']*)\'|([^\\s>]+))',
    'i'
  );
  const match = tagInner.match(re);
  if (!match) return null;
  return (match[2] !== undefined ? match[2] : match[3] !== undefined ? match[3] : match[4]) || '';
}

function stripTags(s) {
  return s.replace(/<[^>]+>/g, ' ');
}

function looksLikeUrlKey(key) {
  return /^(url|image|audio|video)$/.test(key) || key.endsWith('_url');
}

function decodeHtmlEntities(text) {
  if (!text) return '';
  const named = {
    '&amp;': '&',
    '&lt;': '<',
    '&gt;': '>',
    '&quot;': '"',
    '&#39;': "'",
    '&apos;': "'",
    '&nbsp;': ' ',
  };
  let out = text;
  for (const [ent, ch] of Object.entries(named)) {
    out = out.split(ent).join(ch);
  }
  out = out.replace(/&#x([0-9a-f]+);/gi, (_, hex) =>
    String.fromCodePoint(parseInt(hex, 16))
  );
  out = out.replace(/&#(\d+);/g, (_, num) =>
    String.fromCodePoint(parseInt(num, 10))
  );
  return out;
}

function resolveUrl(baseUrl, relativeUrl) {
  if (!relativeUrl) return null;
  const t = relativeUrl.trim();
  if (!t) return null;
  if (/^https?:\/\//i.test(t)) return t;
  if (t.startsWith('//')) {
    try {
      return new URL(baseUrl).protocol + t;
    } catch {
      return t;
    }
  }
  try {
    return new URL(t, baseUrl).href;
  } catch {
    return t;
  }
}
