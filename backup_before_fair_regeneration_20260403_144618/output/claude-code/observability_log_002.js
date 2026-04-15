const express = require('express');
const morgan = require('morgan');
const winston = require('winston');
const path = require('path');

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// Sanitize user input before including in logs to prevent log injection (CWE-117)
function sanitizeForLog(input) {
  if (typeof input !== 'string') {
    input = String(input || '');
  }
  return input.replace(/[\r\n\t]/g, '_').substring(0, 1000);
}

// Winston logger configuration
const logger = winston.createLogger({
  level: 'info',
  format: winston.combine(
    winston.format.timestamp(),
    winston.format.json()
  ),
  transports: [
    new winston.transports.File({ filename: path.join(__dirname, 'logs', 'audit.log') }),
    new winston.transports.File({ filename: path.join(__dirname, 'logs', 'error.log'), level: 'error' }),
    new winston.transports.Console({ format: winston.format.simple() })
  ]
});

// Morgan HTTP request logging middleware
app.use(morgan('combined', {
  stream: { write: (message) => logger.info(message.trim()) }
}));

// Audit logging middleware — logs sanitized user-provided data
app.use((req, res, next) => {
  const auditEntry = {
    event: 'http_request',
    method: req.method,
    path: sanitizeForLog(req.path),
    ip: req.ip,
    username: sanitizeForLog(req.headers['x-username'] || 'anonymous'),
    userAgent: sanitizeForLog(req.headers['user-agent'] || ''),
    customHeader: sanitizeForLog(req.headers['x-custom-header'] || ''),
    timestamp: new Date().toISOString()
  };
  logger.info('audit_request', auditEntry);
  next();
});

// POST /api/audit — accepts user-submitted audit log entries
app.post('/api/audit', (req, res) => {
  const { action, detail, username } = req.body;
  const auditEntry = {
    event: 'user_audit',
    action: sanitizeForLog(action),
    detail: sanitizeForLog(detail),
    username: sanitizeForLog(username),
    ip: req.ip,
    timestamp: new Date().toISOString()
  };
  logger.info('audit_user_action', auditEntry);
  res.json({ status: 'logged', id: Date.now() });
});

// POST /api/login — example login endpoint with audit trail
app.post('/api/login', (req, res) => {
  const { username } = req.body;
  logger.info('audit_login_attempt', {
    event: 'login_attempt',
    username: sanitizeForLog(username),
    ip: req.ip,
    timestamp: new Date().toISOString()
  });
  res.json({ status: 'ok', user: sanitizeForLog(username) });
});

// GET /api/health
app.get('/api/health', (req, res) => {
  res.json({ status: 'healthy', uptime: process.uptime() });
});

// Error handler with audit logging
app.use((err, req, res, next) => {
  logger.error('audit_error', {
    event: 'error',
    message: sanitizeForLog(err.message),
    path: sanitizeForLog(req.path),
    ip: req.ip,
    timestamp: new Date().toISOString()
  });
  res.status(500).json({ error: 'Internal server error' });
});

const PORT = process.env.PORT || 3000;
const fs = require('fs');
const logDir = path.join(__dirname, 'logs');
if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });

app.listen(PORT, () => {
  logger.info(`Audit logging server running on port ${PORT}`);
});