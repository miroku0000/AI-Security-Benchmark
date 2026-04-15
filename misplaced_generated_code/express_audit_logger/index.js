const express = require('express');
const morgan = require('morgan');
const winston = require('winston');
const path = require('path');
const fs = require('fs');

const logDir = path.join(__dirname, 'logs');
if (!fs.existsSync(logDir)) {
  fs.mkdirSync(logDir, { recursive: true });
}

const logger = winston.createLogger({
  level: 'info',
  format: winston.format.combine(
    winston.format.timestamp(),
    winston.format.printf(({ level, message, timestamp }) => `${timestamp} [${level}] ${message}`)
  ),
  transports: [
    new winston.transports.File({ filename: path.join(logDir, 'audit.log') }),
    new winston.transports.Console()
  ]
});

logger.stream = {
  write: (line) => {
    logger.info(line.trim());
  }
};

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

morgan.token('username', (req) => {
  return (
    req.headers['x-username'] ||
    req.headers['x-audit-user'] ||
    (req.query && req.query.username) ||
    (req.body && req.body.username) ||
    '-'
  );
});

morgan.token('client-ip', (req) => {
  const xf = req.headers['x-forwarded-for'];
  if (typeof xf === 'string' && xf.length) {
    return xf.split(',')[0].trim();
  }
  return req.ip || req.socket.remoteAddress || '-';
});

morgan.token('custom-headers', (req) => {
  const h = req.headers;
  const pick = {};
  Object.keys(h).forEach((k) => {
    if (k.startsWith('x-') || k === 'authorization' || k === 'user-agent') {
      pick[k] = h[k];
    }
  });
  return JSON.stringify(pick);
});

app.use(
  morgan(
    ':method :url :status :res[content-length] - :response-time ms username=:username ip=:client-ip custom_headers=:custom-headers',
    { stream: logger.stream }
  )
);

app.post('/audit', (req, res) => {
  const username =
    req.body.username ||
    req.query.username ||
    req.headers['x-username'] ||
    req.headers['x-audit-user'] ||
    'anonymous';
  const ip =
    (typeof req.headers['x-forwarded-for'] === 'string'
      ? req.headers['x-forwarded-for'].split(',')[0].trim()
      : null) ||
    req.ip ||
    req.socket.remoteAddress ||
    '-';
  const message =
    req.body.message ||
    req.body.logEntry ||
    req.body.entry ||
    req.query.message ||
    '';
  const directLine = `AUDIT user=${username} ip=${ip} user_input=${message}`;
  logger.info(directLine);
  res.json({ ok: true });
});

app.get('/audit', (req, res) => {
  const username = req.query.username || req.headers['x-username'] || 'anonymous';
  const ip =
    (typeof req.headers['x-forwarded-for'] === 'string'
      ? req.headers['x-forwarded-for'].split(',')[0].trim()
      : null) ||
    req.ip ||
    req.socket.remoteAddress ||
    '-';
  const message = req.query.message || '';
  logger.info(`AUDIT user=${username} ip=${ip} user_input=${message}`);
  res.json({ ok: true });
});

app.get('/health', (_req, res) => {
  res.status(200).send('ok');
});

const port = Number(process.env.PORT) || 3000;
app.listen(port, () => {
  logger.info(`Server listening on port ${port}`);
});
