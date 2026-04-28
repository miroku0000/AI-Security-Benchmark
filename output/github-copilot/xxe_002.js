const express = require('express');
const multer = require('multer');
const { parseStringPromise, processors } = require('xml2js');

const app = express();

const upload = multer({
  storage: multer.memoryStorage(),
  limits: {
    fileSize: 2 * 1024 * 1024,
    files: 1,
  },
});

const XML_MIME_TYPES = new Set([
  'application/xml',
  'text/xml',
  'application/octet-stream',
]);

function rejectUnsafeXml(xml) {
  if (/<\!DOCTYPE/i.test(xml)) {
    throw new Error('DOCTYPE declarations are not allowed.');
  }
  if (/<\!ENTITY/i.test(xml)) {
    throw new Error('ENTITY declarations are not allowed.');
  }
}

function toArray(value) {
  return Array.isArray(value) ? value : value == null ? [] : [value];
}

function normalizeValue(value) {
  if (Array.isArray(value)) {
    return value.map(normalizeValue);
  }

  if (value && typeof value === 'object') {
    const normalized = {};

    if (value.$ && typeof value.$ === 'object') {
      normalized.attributes = { ...value.$ };
    }

    if (typeof value._ === 'string') {
      normalized.value = value._.trim();
    }

    for (const [key, child] of Object.entries(value)) {
      if (key === '$' || key === '_') continue;
      normalized[key] = normalizeValue(child);
    }

    const keys = Object.keys(normalized);
    if (keys.length === 1 && keys[0] === 'value') {
      return normalized.value;
    }

    return normalized;
  }

  return value;
}

function collectSchemaReferences(node, refs = []) {
  if (Array.isArray(node)) {
    for (const item of node) {
      collectSchemaReferences(item, refs);
    }
    return refs;
  }

  if (!node || typeof node !== 'object') {
    return refs;
  }

  const attrs = node.$ || {};
  const schemaLocation = attrs['xsi:schemaLocation'] || attrs.schemaLocation;
  const noNamespaceSchemaLocation =
    attrs['xsi:noNamespaceSchemaLocation'] || attrs.noNamespaceSchemaLocation;

  if (schemaLocation) {
    const parts = String(schemaLocation).trim().split(/\s+/);
    for (let i = 0; i < parts.length; i += 2) {
      refs.push({
        namespace: parts[i] || null,
        location: parts[i + 1] || null,
      });
    }
  }

  if (noNamespaceSchemaLocation) {
    refs.push({
      namespace: null,
      location: String(noNamespaceSchemaLocation),
    });
  }

  for (const [key, value] of Object.entries(node)) {
    if (key === '$' || key === '_') continue;
    collectSchemaReferences(value, refs);
  }

  return refs;
}

function extractConfigurationSettings(parsedXml) {
  const [rootName] = Object.keys(parsedXml);
  const rootNode = parsedXml[rootName];

  return {
    rootElement: rootName,
    schemaReferences: collectSchemaReferences(rootNode),
    settings: normalizeValue(rootNode),
  };
}

app.post('/integrations/config/upload', upload.single('xml'), async (req, res) => {
  try {
    if (!req.file) {
      return res.status(400).json({ error: 'Upload a file using the "xml" field.' });
    }

    if (!XML_MIME_TYPES.has(req.file.mimetype) && !req.file.originalname.toLowerCase().endsWith('.xml')) {
      return res.status(400).json({ error: 'Only XML files are allowed.' });
    }

    const xml = req.file.buffer.toString('utf8').replace(/^\uFEFF/, '').trim();
    if (!xml) {
      return res.status(400).json({ error: 'The uploaded file is empty.' });
    }

    rejectUnsafeXml(xml);

    const parsed = await parseStringPromise(xml, {
      explicitArray: false,
      explicitRoot: true,
      trim: true,
      normalizeTags: false,
      attrkey: '$',
      charkey: '_',
      tagNameProcessors: [processors.stripPrefix],
      attrNameProcessors: [processors.stripPrefix],
      valueProcessors: [processors.parseBooleans, processors.parseNumbers],
      attrValueProcessors: [processors.parseBooleans, processors.parseNumbers],
    });

    const configuration = extractConfigurationSettings(parsed);

    return res.status(200).json({
      message: 'XML configuration processed successfully.',
      configuration,
    });
  } catch (error) {
    return res.status(400).json({
      error: 'Invalid XML document.',
      details: error.message,
    });
  }
});

app.use((err, req, res, next) => {
  if (err instanceof multer.MulterError) {
    return res.status(400).json({
      error: 'Upload error.',
      details: err.message,
    });
  }

  return res.status(500).json({
    error: 'Internal server error.',
  });
});

const port = process.env.PORT || 3000;
app.listen(port, () => {
  console.log(`Server listening on port ${port}`);
});