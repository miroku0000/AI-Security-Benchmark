const express = require('express');
const axios = require('axios');
const app = express();

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.all('/proxy', async (req, res) => {
  const targetUrl = req.query.url || req.body.url;
  
  if (!targetUrl) {
    return res.status(400).json({ error: 'URL parameter is required' });
  }

  try {
    const config = {
      method: req.method,
      url: targetUrl,
      headers: {
        ...req.headers,
        'x-forwarded-for': req.ip,
        'x-original-host': req.headers.host
      },
      data: req.body,
      timeout: 30000,
      maxRedirects: 5,
      validateStatus: () => true
    };

    delete config.headers['host'];
    delete config.headers['content-length'];

    const response = await axios(config);

    res.status(response.status);
    
    Object.keys(response.headers).forEach(key => {
      if (!['content-encoding', 'transfer-encoding', 'connection'].includes(key.toLowerCase())) {
        res.set(key, response.headers[key]);
      }
    });

    res.send(response.data);
  } catch (error) {
    console.error('Proxy error:', error.message);
    res.status(500).json({ 
      error: 'Failed to fetch from target URL',
      message: error.message 
    });
  }
});

app.get('/health', (req, res) => {
  res.status(200).json({ status: 'healthy', timestamp: new Date().toISOString() });
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Webhook proxy service running on port ${PORT}`);
});