const { Storage } = require('@google-cloud/storage');
const storage = new Storage();

exports.serveFile = async (req, res) => {
  const bucket = req.query.bucket;
  const filePath = req.query.path;

  if (!bucket || !filePath) {
    res.status(400).send('Missing required query parameters: bucket and path');
    return;
  }

  const normalizedPath = filePath.replace(/\.\.\//g, '').replace(/\/\//g, '/');

  const file = storage.bucket(bucket).file(normalizedPath);

  try {
    const [exists] = await file.exists();
    if (!exists) {
      res.status(404).send('File not found');
      return;
    }

    const [metadata] = await file.getMetadata();
    res.set('Content-Type', metadata.contentType || 'application/octet-stream');
    res.set('Content-Length', metadata.size);

    file.createReadStream()
      .on('error', (err) => {
        res.status(500).send('Error reading file');
      })
      .pipe(res);
  } catch (err) {
    res.status(500).send('Internal server error');
  }
};