const dns = require('node:dns').promises;
const net = require('node:net');

const MAX_REDIRECTS = 5;
const MAX_HTML_BYTES = 1024 * 1024;
const REQUEST_TIMEOUT_MS = 8000;
const USER_AGENT = 'LinkMetadataFetcher/1.0';

function ipToBigInt(ip) {
  return ip.split('.').reduce((acc, octet) => (acc << 8n) + BigInt(Number(octet)), 0n);
}

function ipv6ToBigInt(ip) {
  let normalized = ip.toLowerCase();

  if (normalized.startsWith('::ffff:')) {
    const maybeV4 = normalized.slice(7);
    if (net.isIP(maybeV4) === 4) {
      return (0xffffn << 32n) + ipToBigInt(maybeV4);
    }
  }

  const zoneIndex = normalized.indexOf('%');
  if (zoneIndex !== -1) {
    normalized = normalized.slice(0, zoneIndex);
  }

  const hasCompression = normalized.includes('::');
  let parts = [];

  if (hasCompression) {
    const [left, right] = normalized.split('::');
    const leftParts = left ? left.split(':').filter(Boolean) : [];
    const rightParts = right ? right.split(':').filter(Boolean) : [];
    const missing = 8 - (leftParts.length + rightParts.length);
    parts = [...leftParts, ...Array(Math.max(0, missing)).fill('0'), ...rightParts];
  } else {
    parts = normalized.split(':');
  }

  if (parts.length !== 8) {
    throw new Error('Invalid IPv6 address');
  }

  return parts.reduce((acc, part) => (acc << 16n) + BigInt(parseInt(part || '0', 16)), 0n);
}

function isIpv4PrivateOrReserved(ip) {
  const value = ipToBigInt(ip);

  const ranges = [
    ['0.0.0.0', '0.255.255.255'],
    ['10.0.0.0', '10.255.255.255'],
    ['100.64.0.0', '100.127.255.255'],
    ['127.0.0.0', '127.255.255.255'],
    ['169.254.0.0', '169.254.255.255'],
    ['172.16.0.0', '172.31.255.255'],
    ['192.0.0.0', '192.0.0.255'],
    ['192.0.2.0', '192.0.2.255'],
    ['192.168.0.0', '192.168.255.255'],
    ['198.18.0.0', '198.19.255.255'],
    ['198.51.100.0', '198.51.100.255'],
    ['203.0.113.0', '203.0.113.255'],
    ['224.0.0.0', '255.255.255.255']
  ].map(([start, end]) => [ipToBigInt(start), ipToBigInt(end)]);

  return ranges.some(([start, end]) => value >= start && value <= end);
}

function isIpv6PrivateOrReserved(ip) {
  const value = ipv6ToBigInt(ip);

  const ranges = [
    ['::', '::'],
    ['::1', '::1'],
    ['::ffff:0:0', '::ffff:ffff:ffff'],
    ['64:ff9b:1::', '64:ff9b:1:ffff:ffff:ffff:ffff:ffff'],
    ['100::', '100::ffff:ffff:ffff:ffff'],
    ['2001:2::', '2001:2:ffff:ffff:ffff:ffff:ffff:ffff'],
    ['2001:db8::', '2001:db8:ffff:ffff:ffff:ffff:ffff:ffff'],
    ['2001:10::', '2001:1f:ffff:ffff:ffff:ffff:ffff:ffff'],
    ['fc00::', 'fdff:ffff:ffff:ffff:ffff:ffff:ffff:ffff'],
    ['fe80::', 'febf:ffff:ffff:ffff:ffff:ffff:ffff:ffff'],
    ['ff00::', 'ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff']
  ].map(([start, end]) => [ipv6ToBigInt(start), ipv6ToBigInt(end)]);

  return ranges.some(([start, end]) => value >= start && value <= end);
}

function isPrivateOrReservedIp(ip) {
  const family = net.isIP(ip);
  if (family === 4) {
    return isIpv4PrivateOrReserved(ip);
  }
  if (family === 6) {
    return isIpv6PrivateOrReserved(ip);
  }
  return true;
}

async function assertSafeHostname(hostname) {
  if (!hostname) {
    throw new Error('Missing hostname');
  }

  const normalized = hostname.replace(/\.$/, '').toLowerCase();

  if (normalized === 'localhost' || normalized.endsWith('.localhost')) {
    throw new Error('Hostname is not allowed');
  }

  const directIpFamily = net.isIP(normalized);
  if (directIpFamily && isPrivateOrReservedIp(normalized)) {
    throw new Error('IP address is not allowed');
  }

  const records = await dns.lookup(normalized, { all: true, verbatim: true });
  if (!records.length) {
    throw new Error('Hostname did not resolve');
  }

  for (const record of records) {
    if (isPrivateOrReservedIp(record.address)) {
      throw new Error('Resolved address is not allowed');
    }
  }
}

function decodeHtmlEntities(input) {
  return input
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&#x27;/gi, "'")
    .replace(/&#x2F;/gi, '/')
    .replace(/&#(\d+);/g, (_, n) => {
      const code = Number(n);
      return Number.isFinite(code) ? String.fromCodePoint(code) : _;
    })
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => {
      const code = parseInt(hex, 16);
      return Number.isFinite(code) ? String.fromCodePoint(code) : _;
    });
}

function stripTags(input) {
  return input.replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ')
    .replace(/<[^>]+>/g, ' ');
}

function normalizeText(input) {
  return decodeHtmlEntities(stripTags(input)).replace(/\s+/g, ' ').trim();
}

function extractMetaTagContent(html, attrName, attrValue) {
  const regex = new RegExp(
    `<meta\\b[^>]*\\b${attrName}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s"'=<>` + '`' + `]+))[^>]*\\bcontent\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s"'=<>` + '`' + `]+))[^>]*>`,
    'i'
  );
  const reverseRegex = new RegExp(
    `<meta\\b[^>]*\\bcontent\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s"'=<>` + '`' + `]+))[^>]*\\b${attrName}\\s*=\\s*("([^"]*)"|'([^']*)'|([^\\s"'=<>` + '`' + `]+))[^>]*>`,
    'i'
  );

  const direct = html.match(regex);
  if (direct) {
    const foundAttr = (direct[2] || direct[3] || direct[4] || '').trim().toLowerCase();
    if (foundAttr === attrValue.toLowerCase()) {
      return normalizeText(direct[6] || direct[7] || direct[8] || '');
    }
  }

  const reverse = html.match(reverseRegex);
  if (reverse) {
    const foundAttr = (reverse[6] || reverse[7] || reverse[8] || '').trim().toLowerCase();
    if (foundAttr === attrValue.toLowerCase()) {
      return normalizeText(reverse[2] || reverse[3] || reverse[4] || '');
    }
  }

  return null;
}

function extractAllOpenGraph(html) {
  const og = {};
  const tagRegex = /<meta\b[^>]*>/gi;
  const attrRegex = /\b([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*("([^"]*)"|'([^']*)'|([^\s"'=<>`]+))/g;

  for (const tag of html.match(tagRegex) || []) {
    const attrs = {};
    let match;
    while ((match = attrRegex.exec(tag)) !== null) {
      attrs[match[1].toLowerCase()] = match[3] || match[4] || match[5] || '';
    }

    const property = (attrs.property || '').trim().toLowerCase();
    const content = normalizeText(attrs.content || '');

    if (property.startsWith('og:') && content) {
      og[property] = content;
    }
  }

  return og;
}

function extractTitle(html) {
  const match = html.match(/<title\b[^>]*>([\s\S]*?)<\/title>/i);
  return match ? normalizeText(match[1]) : null;
}

function extractDescription(html) {
  return (
    extractMetaTagContent(html, 'name', 'description') ||
    extractMetaTagContent(html, 'property', 'description') ||
    extractMetaTagContent(html, 'property', 'og:description')
  );
}

function json(res, statusCode, body) {
  res.status(statusCode).set('Content-Type', 'application/json; charset=utf-8').send(JSON.stringify(body));
}

async function fetchHtmlWithRedirects(inputUrl) {
  let currentUrl = inputUrl;

  for (let redirectCount = 0; redirectCount <= MAX_REDIRECTS; redirectCount += 1) {
    const url = new URL(currentUrl);

    if (!['http:', 'https:'].includes(url.protocol)) {
      throw new Error('Only HTTP(S) URLs are allowed');
    }

    if (url.username || url.password) {
      throw new Error('Credentials in URL are not allowed');
    }

    await assertSafeHostname(url.hostname);

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);

    let response;
    try {
      response = await fetch(url.toString(), {
        method: 'GET',
        redirect: 'manual',
        signal: controller.signal,
        headers: {
          'User-Agent': USER_AGENT,
          'Accept': 'text/html,application/xhtml+xml'
        }
      });
    } finally {
      clearTimeout(timeout);
    }

    const status = response.status;
    if ([301, 302, 303, 307, 308].includes(status)) {
      const location = response.headers.get('location');
      if (!location) {
        throw new Error('Redirect response missing location');
      }
      currentUrl = new URL(location, url).toString();
      continue;
    }

    if (!response.ok) {
      throw new Error(`Upstream responded with status ${status}`);
    }

    const contentType = (response.headers.get('content-type') || '').toLowerCase();
    if (!contentType.includes('text/html') && !contentType.includes('application/xhtml+xml')) {
      throw new Error('URL did not return HTML');
    }

    const reader = response.body.getReader();
    const chunks = [];
    let totalBytes = 0;

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      totalBytes += value.byteLength;
      if (totalBytes > MAX_HTML_BYTES) {
        throw new Error('HTML response exceeded size limit');
      }
      chunks.push(Buffer.from(value));
    }

    return {
      finalUrl: url.toString(),
      html: Buffer.concat(chunks).toString('utf8')
    };
  }

  throw new Error('Too many redirects');
}

exports.fetchUrlMetadata = async (req, res) => {
  try {
    const rawUrl =
      (req.body && typeof req.body === 'object' && req.body.url) ||
      req.query.url;

    if (typeof rawUrl !== 'string' || rawUrl.trim() === '') {
      return json(res, 400, { error: 'Missing required "url" parameter' });
    }

    let parsed;
    try {
      parsed = new URL(rawUrl.trim());
    } catch {
      return json(res, 400, { error: 'Invalid URL' });
    }

    const { finalUrl, html } = await fetchHtmlWithRedirects(parsed.toString());
    const openGraph = extractAllOpenGraph(html);

    const title = openGraph['og:title'] || extractTitle(html);
    const description = openGraph['og:description'] || extractDescription(html);

    return json(res, 200, {
      url: finalUrl,
      metadata: {
        title: title || null,
        description: description || null,
        openGraph
      }
    });
  } catch (error) {
    const message =
      error && typeof error.message === 'string'
        ? error.message
        : 'Failed to fetch metadata';

    const statusCode =
      /not allowed|invalid|missing|required|only http/i.test(message) ? 400 : 502;

    return json(res, statusCode, { error: message });
  }
};