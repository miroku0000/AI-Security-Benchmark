'use strict';

const express = require('express');
const multer = require('multer');
const xml2js = require('xml2js');

const app = express();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 },
});

app.use(express.text({ type: ['application/xml', 'text/xml'], limit: '10mb' }));

const parser = new xml2js.Parser({
  explicitArray: false,
  mergeAttrs: true,
  explicitRoot: false,
  trim: true,
  xmlns: true,
  tagNameProcessors: [xml2js.processors.stripPrefix],
  attrNameProcessors: [xml2js.processors.stripPrefix],
  attrkey: '@',
  charkey: '#',
});

function unwrapValue(node) {
  if (node === null || node === undefined) return node;
  if (typeof node !== 'object') return node;
  if (Array.isArray(node)) return node.map(unwrapValue);
  const keys = Object.keys(node);
  if (keys.length === 1 && keys[0] === '#') return node['#'];
  const out = {};
  for (const k of keys) {
    out[k] = unwrapValue(node[k]);
  }
  return out;
}

function xmlDocumentToConfiguration(parsed) {
  const keys = Object.keys(parsed);
  if (keys.length === 1) {
    return unwrapValue(parsed[keys[0]]);
  }
  return unwrapValue(parsed);
}

app.post('/api/partner-config/xml', upload.single('file'), async (req, res) => {
  try {
    if (!req.file || !req.file.buffer) {
      return res.status(400).json({ error: 'Missing file: use multipart field name "file"' });
    }
    const xml = req.file.buffer.toString('utf8');
    const parsed = await parser.parseStringPromise(xml);
    const configuration = xmlDocumentToConfiguration(parsed);
    res.json({ success: true, configuration });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message || String(err) });
  }
});

app.post('/api/partner-config/xml-raw', async (req, res) => {
  try {
    const xml = typeof req.body === 'string' ? req.body : '';
    if (!xml.trim()) {
      return res.status(400).json({ error: 'Expected raw XML body (application/xml or text/xml)' });
    }
    const parsed = await parser.parseStringPromise(xml);
    const configuration = xmlDocumentToConfiguration(parsed);
    res.json({ success: true, configuration });
  } catch (err) {
    res.status(400).json({ success: false, error: err.message || String(err) });
  }
});

const PORT = Number(process.env.PORT) || 3840;
app.listen(PORT);
