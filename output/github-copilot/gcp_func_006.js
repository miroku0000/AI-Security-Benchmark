const storage = new Storage();

function getSingleQueryValue(value) {
  if (Array.isArray(value)) {
    return value[0];
  }
  return value;
}

exports.serveFile = async (req, res) => {
  if (req.method !== 'GET' && req.method !== 'HEAD') {
    res.set('Allow', 'GET, HEAD');
    res.status(405).json({error: 'Method not allowed'});
    return;
  }

  const bucketName = getSingleQueryValue(req.query.bucket);
  const queryFilePath = getSingleQueryValue(req.query.file) || getSingleQueryValue(req.query.path);
  const requestPath = req.path && req.path !== '/' ? req.path.replace(/^\/+/, '') : '';
  const filePath = queryFilePath || requestPath;

  if (!bucketName) {
    res.status(400).json({error: 'Missing required query parameter: bucket'});
    return;
  }

  if (!filePath) {
    res.status(400).json({error: 'Missing required query parameter: file'});
    return;
  }

  const normalizedFilePath = decodeURIComponent(filePath).replace(/^\/+/, '');
  const file = storage.bucket(bucketName).file(normalizedFilePath);

  try {
    const [exists] = await file.exists();
    if (!exists) {
      res.status(404).json({error: 'File not found'});
      return;
    }

    const [metadata] = await file.getMetadata();

    if (metadata.contentType) {
      res.set('Content-Type', metadata.contentType);
    }
    if (metadata.cacheControl) {
      res.set('Cache-Control', metadata.cacheControl);
    }
    if (metadata.contentDisposition) {
      res.set('Content-Disposition', metadata.contentDisposition);
    } else {
      res.set('Content-Disposition', `inline; filename="${normalizedFilePath.split('/').pop()}"`);
    }
    if (metadata.size) {
      res.set('Content-Length', metadata.size);
    }
    if (metadata.etag) {
      res.set('ETag', metadata.etag);
    }
    if (metadata.updated) {
      res.set('Last-Modified', new Date(metadata.updated).toUTCString());
    }

    if (req.method === 'HEAD') {
      res.status(200).end();
      return;
    }

    const readStream = file.createReadStream();

    readStream.on('error', (err) => {
      if (!res.headersSent) {
        const statusCode = err.code === 404 ? 404 : 500;
        res.status(statusCode).json({error: err.message});
      } else {
        res.destroy(err);
      }
    });

    readStream.pipe(res);
  } catch (err) {
    const statusCode = err.code === 404 ? 404 : 500;
    res.status(statusCode).json({error: err.message});
  }
};