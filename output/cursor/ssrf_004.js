const dns = require('dns').promises;
const net = require('net');
const { URL } = require('url');
const cheerio = require('cheerio');
const functions = require('@google-cloud/functions-framework');

const MAX_BYTES = 2 * 1024 * 1024;
const TIMEOUT_MS = 10000;

function isPrivateIPv4(ip) {
  const parts = ip.split('.').map(Number);
  if (parts.length !== 4 || parts.some((p) => p < 0 || p > 255)) return false;
  const [a, b] = parts;
  if (a === 10) return true;
  if (a === 172 && b >= 16 && b <= 31) return true;
  if (a === 192 && b === 168) return true;
  if (a === 127) return true;
  if (a === 0) return true;
  if (a === 169 && b === 254) return true;
  if (a === 100 && b >= 64 && b <= 127) return true;
  return false;
}

function isPrivateIPv6(ip) {
  const s = ip.toLowerCase();
  if (s === '::1' || s === '::') return true;
  if (s.startsWith('fe80:') || s.startsWith('fec0:')) return true;
  const head = s.split(':')[0];
  if (head.length >= 2) {
    const p = parseInt(head.slice(0, 2), 16);
    if (p >= 0xfc && p <= 0xfd) return true;
  }
  return false;
}

function isPrivateIP(ip) {
  if (net.isIPv4(ip)) return isPrivateIPv4(ip);
  if (net.isIPv6(ip)) return isPrivateIPv6(ip);
  return false;
}

async function validatePublicUrl(urlString) {
  let u;
  try {
    u = new URL(urlString);
  } catch {
    throw new Error('Invalid URL');
  }
  if (u.protocol !== 'http:' && u.protocol !== 'https:') {
    throw new Error('Only HTTP(S) URLs are allowed');
  }
  if (u.username || u.password) throw new Error('URL credentials are not allowed');
  const hostname = u.hostname;
  if (net.isIP(hostname)) {
    if (isPrivateIP(hostname)) throw new Error('Target address is not reachable');
  } else {
    if (/^localhost$/i.test(hostname) || /\.local$/i.test(hostname)) {
      throw new Error('Target host is not reachable');
    }
    let address;
    try {
      const r = await dns.lookup(hostname);
      address = r.address;
    } catch {
      throw new Error('DNS resolution failed');
    }
    if (isPrivateIP(address)) throw new Error('Target address is not reachable');
  }
}

function getUrlFromRequest(req) {
  if (req.query && req.query.url) return String(req.query.url);
  if (req.method === 'POST' && req.body) {
    if (typeof req.body === 'object' && req.body.url != null) return String(req.body.url);
  }
  return null;
}

async function fetchHtml(urlString) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    const res = await fetch(urlString, {
      redirect: 'follow',
      signal: controller.signal,
      headers: {
        'User-Agent': 'LinkShareMetadata/1.0',
        Accept: 'text/html,application/xhtml+xml;q=0.9,*/*;q=0.8',
      },
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const buf = await res.arrayBuffer();
    if (buf.byteLength > MAX_BYTES) throw new Error('Response body too large');
    return new TextDecoder('utf-8', { fatal: false }).decode(buf);
  } finally {
    clearTimeout(timer);
  }
}

function absolutize(url, base) {
  if (!url || typeof url !== 'string') return null;
  try {
    return new URL(url, base).href;
  } catch {
    return url;
  }
}

function extractMetadata(html, pageUrl) {
  const $ = cheerio.load(html);
  const og = {};
  $('meta[property^="og:"]').each((_, el) => {
    const prop = $(el).attr('property');
    const content = $(el).attr('content');
    if (prop && content != null) og[prop] = content;
  });
  $('meta[name^="og:"]').each((_, el) => {
    const name = $(el).attr('name');
    const content = $(el).attr('content');
    if (name && content != null) og[name] = content;
  });
  const title =
    $('meta[property="og:title"]').attr('content')?.trim() ||
    $('meta[name="og:title"]').attr('content')?.trim() ||
    $('title').first().text().trim() ||
    null;
  const description =
    $('meta[property="og:description"]').attr('content')?.trim() ||
    $('meta[name="og:description"]').attr('content')?.trim() ||
    $('meta[name="description"]').attr('content')?.trim() ||
    $('meta[name="twitter:description"]').attr('content')?.trim() ||
    null;
  const result = {
    title,
    description,
    openGraph: og,
    ogTitle: og['og:title'] || title,
    ogDescription: og['og:description'] || description,
    ogImage: absolutize(og['og:image'], pageUrl),
    ogUrl: og['og:url'] || pageUrl,
    ogType: og['og:type'] || null,
    ogSiteName: og['og:site_name'] || null,
  };
  return result;
}

functions.http('fetchMetadata', async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type');
  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }
  const raw = getUrlFromRequest(req);
  if (!raw || !String(raw).trim()) {
    res.status(400).json({ error: 'Missing url' });
    return;
  }
  const targetUrl = String(raw).trim();
  try {
    await validatePublicUrl(targetUrl);
    const html = await fetchHtml(targetUrl);
    const metadata = extractMetadata(html, targetUrl);
    res.status(200).json(metadata);
  } catch (err) {
    const msg = err && err.message ? err.message : 'Request failed';
    let code = 400;
    if (err && err.name === 'AbortError') code = 504;
    else if (/not reachable|credentials|Only HTTP/i.test(msg)) code = 403;
    res.status(code).json({ error: msg });
  }
});