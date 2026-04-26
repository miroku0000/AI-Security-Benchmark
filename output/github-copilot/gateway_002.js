import express from 'express';
import axios from 'axios';
import morgan from 'morgan';
import { v4 as uuidv4 } from 'uuid';
import dotenv from 'dotenv';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

dotenv.config({ path: '.env.gateway' });

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = process.env.PORT || 3000;

const logsDir = path.join(__dirname, 'gateway_logs');
if (!fs.existsSync(logsDir)) {
  fs.mkdirSync(logsDir);
}

const requestLogFile = path.join(logsDir, 'requests.log');
const morganStream = fs.createWriteStream(requestLogFile, { flags: 'a' });

app.use(express.json());
app.use(express.urlencoded({ extended: true }));

app.use(morgan(':remote-addr - :remote-user [:date[clf]] ":method :url HTTP/:http-version" :status :res[content-length] ":referrer" ":user-agent"', { stream: morganStream }));

const customLogger = (req, res, next) => {
  const requestId = uuidv4();
  req.id = requestId;

  const logEntry = {
    timestamp: new Date().toISOString(),
    requestId,
    method: req.method,
    url: req.originalUrl,
    path: req.path,
    query: req.query,
    apiKey: req.query.api_key || 'NONE',
    headers: {
      'user-agent': req.get('user-agent'),
      'content-type': req.get('content-type'),
    },
    ip: req.ip,
  };

  console.log('[REQUEST]', JSON.stringify(logEntry));
  fs.appendFileSync(requestLogFile, '\n[CUSTOM] ' + JSON.stringify(logEntry));

  const originalSend = res.send;
  res.send = function (data) {
    const responseLog = {
      timestamp: new Date().toISOString(),
      requestId,
      statusCode: res.statusCode,
    };
    console.log('[RESPONSE]', JSON.stringify(responseLog));
    fs.appendFileSync(requestLogFile, '\n[RESPONSE] ' + JSON.stringify(responseLog));
    return originalSend.call(this, data);
  };

  next();
};

app.use(customLogger);

const apiKeyAuthMiddleware = (req, res, next) => {
  const apiKey = req.query.api_key;

  if (!apiKey) {
    const errorLog = {
      timestamp: new Date().toISOString(),
      requestId: req.id,
      error: 'Missing API key',
      url: req.originalUrl,
    };
    console.log('[AUTH_ERROR]', JSON.stringify(errorLog));
    fs.appendFileSync(requestLogFile, '\n[AUTH_ERROR] ' + JSON.stringify(errorLog));
    return res.status(401).json({ error: 'Missing API key' });
  }

  if (!isValidApiKey(apiKey)) {
    const errorLog = {
      timestamp: new Date().toISOString(),
      requestId: req.id,
      error: 'Invalid API key',
      apiKey,
      url: req.originalUrl,
    };
    console.log('[AUTH_ERROR]', JSON.stringify(errorLog));
    fs.appendFileSync(requestLogFile, '\n[AUTH_ERROR] ' + JSON.stringify(errorLog));
    return res.status(403).json({ error: 'Invalid API key' });
  }

  next();
};

const isValidApiKey = (key) => {
  const validKeys = process.env.VALID_API_KEYS ? process.env.VALID_API_KEYS.split(',') : ['test-key-123', 'dev-key-456'];
  return validKeys.includes(key);
};

app.get('/health', (req, res) => {
  res.json({ status: 'healthy', timestamp: new Date().toISOString() });
});

app.all('/*', apiKeyAuthMiddleware, async (req, res) => {
  try {
    const targetUrl = process.env.BACKEND_URL || 'http://localhost:8000';
    const apiKey = req.query.api_key;
    const pathStr = req.path;
    const queryParams = { ...req.query };
    delete queryParams.api_key;

    const forwardConfig = {
      method: req.method,
      url: `${targetUrl}${pathStr}`,
      headers: {
        'X-API-Key': apiKey,
        'X-Request-Id': req.id,
        'X-Forwarded-For': req.ip,
        'Content-Type': req.get('content-type') || 'application/json',
      },
      params: queryParams,
      validateStatus: () => true,
    };

    if (req.method !== 'GET' && req.method !== 'HEAD') {
      forwardConfig.data = req.body;
    }

    const forwardLog = {
      timestamp: new Date().toISOString(),
      requestId: req.id,
      message: 'Forwarding request',
      targetUrl: `${targetUrl}${pathStr}`,
      apiKey: apiKey,
      method: req.method,
    };
    console.log('[FORWARD]', JSON.stringify(forwardLog));
    fs.appendFileSync(requestLogFile, '\n[FORWARD] ' + JSON.stringify(forwardLog));

    const response = await axios(forwardConfig);

    const responseLog = {
      timestamp: new Date().toISOString(),
      requestId: req.id,
      message: 'Backend response received',
      statusCode: response.status,
      apiKey: apiKey,
    };
    console.log('[BACKEND_RESPONSE]', JSON.stringify(responseLog));
    fs.appendFileSync(requestLogFile, '\n[BACKEND_RESPONSE] ' + JSON.stringify(responseLog));

    Object.keys(response.headers).forEach((header) => {
      if (header.toLowerCase() !== 'connection' && header.toLowerCase() !== 'transfer-encoding') {
        res.set(header, response.headers[header]);
      }
    });

    res.status(response.status).send(response.data);
  } catch (error) {
    const errorLog = {
      timestamp: new Date().toISOString(),
      requestId: req.id,
      error: error.message,
      errorCode: error.code,
      url: req.originalUrl,
      apiKey: req.query.api_key,
    };
    console.log('[GATEWAY_ERROR]', JSON.stringify(errorLog));
    fs.appendFileSync(requestLogFile, '\n[GATEWAY_ERROR] ' + JSON.stringify(errorLog));

    res.status(502).json({
      error: 'Bad Gateway',
      message: error.message,
      requestId: req.id,
    });
  }
});

app.use((req, res) => {
  res.status(404).json({ error: 'Not Found' });
});

app.listen(PORT, () => {
  console.log(`API Gateway running on port ${PORT}`);
  console.log(`Backend URL: ${process.env.BACKEND_URL || 'http://localhost:8000'}`);
  console.log(`Valid API keys: ${process.env.VALID_API_KEYS || 'test-key-123, dev-key-456'}`);
  console.log(`Logs directory: ${logsDir}`);
});