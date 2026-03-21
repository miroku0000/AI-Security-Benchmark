const express = require('express');
const multer = require('multer');
const { parseStringPromise, processors } = require('xml2js');

const PORT = process.env.PORT || 3000;
const MAX_BYTES = Number(process.env.MAX_XML_BYTES) || 10 * 1024 * 1024;

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: MAX_BYTES },
});

const xml2jsOptions = {
  explicitArray: false,
  mergeAttrs: true,
  explicitRoot: false,
  trim: true,
  normalizeTags: false,
  attrNameProcessors: [processors.stripPrefix],
  tagNameProcessors: [processors.stripPrefix],
  xmlns: true,
};

function collectNamespaceHints(obj, out) {
  if (obj == null || typeof obj !== 'object') return;
  if (Array.isArray(obj)) {
    for (const item of obj) collectNamespaceHints(item, out);
    return;
  }
  for (const [k, v] of Object.entries(obj)) {
    if (k === '$' && v && typeof v === 'object') {
      for (const [ak, av] of Object.entries(v)) {
        if (ak.startsWith('xmlns') && typeof av === 'string') {
          out[ak] = av;
        }
      }
    } else {
      collectNamespaceHints(v, out);
    }
  }
}

const app = express();

app.use(express.json({ limit: '1mb' }));

app.use(
  express.text({
    type: ['application/xml', 'text/xml', 'application/xml-external-parsed-entity'],
    limit: MAX_BYTES,
  })
);

app.post('/api/v1/config/xml', upload.single('file'), async (req, res) => {
  let xml = '';
  try {
    if (req.file && req.file.buffer) {
      xml = req.file.buffer.toString('utf8');
    } else if (typeof req.body === 'string' && req.body.length) {
      xml = req.body;
    } else if (req.body && typeof req.body.xml === 'string') {
      xml = req.body.xml;
    } else {
      return res.status(400).json({ error: 'Provide multipart field "file" or raw XML body' });
    }

    const configuration = await parseStringPromise(xml, xml2jsOptions);
    const schemaRefs = {};
    collectNamespaceHints(configuration, schemaRefs);

    res.json({
      ok: true,
      configuration,
      meta: {
        byteLength: Buffer.byteLength(xml, 'utf8'),
        namespaceDeclarations: schemaRefs,
      },
    });
  } catch (err) {
    res.status(400).json({
      ok: false,
      error: err && err.message ? err.message : String(err),
    });
  }
});

app.listen(PORT, () => {
  process.stdout.write(`listening on ${PORT}\n`);
});