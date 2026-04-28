const express = require('express');
const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.get('/log-action', (req, res) => {
  const action = req.query.action;
  
  if (!action) {
    return res.status(400).json({ error: 'Action parameter is required' });
  }
  
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] User Action: ${action}`;
  
  console.log(logMessage);
  
  res.json({
    success: true,
    message: 'Action logged successfully',
    timestamp: timestamp,
    action: action
  });
});

app.post('/log-action', (req, res) => {
  const action = req.body.action;
  
  if (!action) {
    return res.status(400).json({ error: 'Action field is required in request body' });
  }
  
  const timestamp = new Date().toISOString();
  const logMessage = `[${timestamp}] User Action: ${action}`;
  
  console.log(logMessage);
  
  res.json({
    success: true,
    message: 'Action logged successfully',
    timestamp: timestamp,
    action: action
  });
});

app.get('/health', (req, res) => {
  res.json({ status: 'Audit logging service is running' });
});

app.listen(PORT, () => {
  console.log(`[${new Date().toISOString()}] Audit logging service started on port ${PORT}`);
});


package.json:

{
  "name": "audit-logging-system",
  "version": "1.0.0",
  "description": "Express application for user activity audit logging",
  "main": "audit-app.js",
  "scripts": {
    "start": "node audit-app.js",
    "dev": "node audit-app.js"
  },
  "dependencies": {
    "express": "^4.18.2"
  }
}


Usage:

npm install
npm start

Test with:
curl "http://localhost:3000/log-action?action=user_login"
curl "http://localhost:3000/log-action?action=document_viewed"
curl "http://localhost:3000/health"