'use strict';

const express = require('express');
const multer = require('multer');
const xml2js = require('xml2js');

const app = express();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 },
});

const parser = new xml2js.Parser({
  explicitArray: false,
  mergeAttrs: true,
  explicitRoot: true,
  trim: true,
  ignoreAttrs: false,
  xmlns: true,
});

function stripDoctype(xml) {
  return String(xml).replace(/<!DOCTYPE[\s\S]*?>/gi, '');
}

function collectSchemaHints(obj, out) {
  if (!obj || typeof obj !== 'object') {
    return;
  }
  if (Array.isArray(obj)) {
    for (const item of obj) {
      collectSchemaHints(item, out);
    }
    return;
  }
  for (const [k, v] of Object.entries(obj)) {
    if (/schemaLocation$/i.test(k) || k === 'schemaLocation' || k.endsWith(':schemaLocation')) {
      out[k] = v;
    }
    if (/noNamespaceSchemaLocation$/i.test(k) || k.endsWith(':noNamespaceSchemaLocation')) {
      out[k] = v;
    }
    if (v && typeof v === 'object') {
      collectSchemaHints(v, out);
    }
  }
}

function extractConfiguration(parsed) {
  if (!parsed || typeof parsed !== 'object') {
    return { configuration: {}, schemaHints: {} };
  }
  const keys = Object.keys(parsed);
  if (keys.length === 0) {
    return { configuration: {}, schemaHints: {} };
  }
  const rootKey = keys[0];
  const root = parsed[rootKey];
  const schemaHints = {};
  collectSchemaHints(root, schemaHints);
  if (root && typeof root === 'object' && !Array.isArray(root)) {
    const lower = String(rootKey).toLowerCase();
    if (lower === 'configuration' || lower === 'config' || lower === 'settings') {
      return { configuration: root, schemaHints };
    }
  }
  return { configuration: parsed, schemaHints };
}

app.post('/integrations/xml-config', upload.single('file'), async (req, res) => {
  try {
    if (!req.file || !req.file.buffer || req.file.buffer.length === 0) {
      res.status(400).json({ error: 'missing_file' });
      return;
    }
    const xml = stripDoctype(req.file.buffer.toString('utf8'));
    const parsed = await parser.parseStringPromise(xml);
    const { configuration, schemaHints } = extractConfiguration(parsed);
    res.status(200).json({ ok: true, configuration, schemaHints });
  } catch (err) {
    res.status(400).json({
      error: 'parse_failed',
      message: err && err.message ? err.message : String(err),
    });
  }
});

const port = Number(process.env.PORT) || 3000;
app.listen(port);

module.exports = app;
