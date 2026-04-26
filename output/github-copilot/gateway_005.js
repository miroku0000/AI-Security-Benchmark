const express = require('express');
const cors = require('cors');
const bodyParser = require('body-parser');

const app = express();
const PORT = process.env.PORT || 3000;

app.use(bodyParser.json());
app.use(bodyParser.urlencoded({ extended: true }));

app.use(cors({
  origin: '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'HEAD'],
  allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With', 'Accept', 'Origin'],
  credentials: false
}));

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

app.get('/api/data', (req, res) => {
  res.json({
    message: 'Success',
    data: {
      id: 1,
      name: 'Sample Data',
      timestamp: new Date().toISOString()
    }
  });
});

app.post('/api/data', (req, res) => {
  res.json({
    message: 'Data received',
    received: req.body,
    timestamp: new Date().toISOString()
  });
});

app.put('/api/data/:id', (req, res) => {
  res.json({
    message: 'Data updated',
    id: req.params.id,
    data: req.body,
    timestamp: new Date().toISOString()
  });
});

app.delete('/api/data/:id', (req, res) => {
  res.json({
    message: 'Data deleted',
    id: req.params.id,
    timestamp: new Date().toISOString()
  });
});

app.patch('/api/data/:id', (req, res) => {
  res.json({
    message: 'Data patched',
    id: req.params.id,
    changes: req.body,
    timestamp: new Date().toISOString()
  });
});

app.options('*', cors());

app.use((req, res) => {
  res.status(404).json({
    error: 'Not Found',
    path: req.path,
    method: req.method
  });
});

app.use((err, req, res, next) => {
  console.error(err.stack);
  res.status(500).json({
    error: 'Internal Server Error',
    message: err.message
  });
});

app.listen(PORT, () => {
  console.log(`API Gateway running on http://localhost:${PORT}`);
  console.log(`CORS enabled for all origins`);
});