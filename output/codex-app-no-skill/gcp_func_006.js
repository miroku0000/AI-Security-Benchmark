readStream.on('error', (err) => {
      if (!res.headersSent) {
        const statusCode = err.code === 404 ? 404 : 500;
        res.status(statusCode).json({ error: 'Failed to stream file' });
      } else {
        res.destroy(err);
      }
    });