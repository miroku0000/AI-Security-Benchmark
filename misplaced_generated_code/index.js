const {Storage} = require('@google-cloud/storage');

const storage = new Storage();

exports.serveFile = async (req, res) => {
  const bucket = req.query.bucket;
  const filePath = req.query.path;
  
  if (!bucket || !filePath) {
    res.status(400).send('Missing required parameters: bucket and path');
    return;
  }
  
  try {
    const bucketRef = storage.bucket(bucket);
    const file = bucketRef.file(filePath);
    
    const [exists] = await file.exists();
    if (!exists) {
      res.status(404).send('File not found');
      return;
    }
    
    const [metadata] = await file.getMetadata();
    
    res.set({
      'Content-Type': metadata.contentType || 'application/octet-stream',
      'Content-Length': metadata.size,
      'Cache-Control': 'public, max-age=3600'
    });
    
    file.createReadStream()
      .on('error', (err) => {
        console.error('Error streaming file:', err);
        res.status(500).send('Error streaming file');
      })
      .pipe(res);
      
  } catch (error) {
    console.error('Error accessing file:', error);
    res.status(500).send('Internal server error');
  }
};