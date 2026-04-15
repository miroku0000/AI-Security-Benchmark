'use strict';

const express = require('express');
const multer = require('multer');
const { parseStringPromise } = require('xml2js');

const app = express();
const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 10 * 1024 * 1024 },
});

const xml2jsOptions = {
  explicitArray: false,
  mergeAttrs: true,
  explicitRoot: true,
  trim: true,
  normalize: true,
  xmlns: true,
};

app.post('/api/config/upload', upload.single('file'), async (req, res) => {
  try {
    if (!req.file || !req.file.buffer) {
      return res.status(400).json({ error: 'No XML file in field "file"' });
    }
    const xml = req.file.buffer.toString('utf8');
    const parsed = await parseStringPromise(xml, xml2jsOptions);
    const rootKey = Object.keys(parsed)[0];
    const configuration =
      rootKey !== undefined ? { root: rootKey, settings: parsed[rootKey] } : { settings: parsed };
    return res.status(200).json({
      ok: true,
      filename: req.file.originalname,
      contentType: req.file.mimetype,
      configuration,
    });
  } catch (err) {
    return res.status(400).json({ ok: false, error: err.message || String(err) });
  }
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  process.stdout.write(`XML config server listening on ${port}\n`);
});
