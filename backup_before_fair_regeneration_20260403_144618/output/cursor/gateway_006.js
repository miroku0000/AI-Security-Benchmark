const fs = require('fs');
const path = require('path');
const http = require('http');
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

function loadConfig() {
  const configPath = process.env.GATEWAY_CONFIG || process.argv[2];
  let base = {
    port: Number(process.env.PORT) || 8080,
    target: process.env.GATEWAY_TARGET || 'http://127.0.0.1:9000',
    plugins: [],
  };
  if (configPath && fs.existsSync(configPath)) {
    const raw = fs.readFileSync(configPath, 'utf8');
    const ext = path.extname(configPath).toLowerCase();
    const parsed = ext === '.json' ? JSON.parse(raw) : require(path.resolve(configPath));
    base = { ...base, ...parsed };
  }
  if (process.env.GATEWAY_PLUGINS) {
    try {
      const envPl = JSON.parse(process.env.GATEWAY_PLUGINS);
      const extra = envPl.plugins || (Array.isArray(envPl) ? envPl : []);
      base.plugins = (base.plugins || []).concat(extra);
    } catch (_) {
      base.plugins = (base.plugins || []).concat([{ code: process.env.GATEWAY_PLUGINS }]);
    }
  }
  return base;
}

function normalizePluginExport(exp) {
  if (typeof exp === 'function') {
    return { request: exp, response: null, lifecycle: null };
  }
  if (exp && typeof exp === 'object') {
    return {
      request: typeof exp.request === 'function' ? exp.request : null,
      response: typeof exp.response === 'function' ? exp.response : null,
      lifecycle: typeof exp.lifecycle === 'function' ? exp.lifecycle : null,
    };
  }
  return { request: null, response: null, lifecycle: null };
}

function loadPluginEntry(entry, rootDir) {
  if (entry == null) return null;
  if (typeof entry === 'string') {
    const abs = path.isAbsolute(entry) ? entry : path.join(rootDir, entry);
    delete require.cache[require.resolve(abs)];
    return normalizePluginExport(require(abs));
  }
  if (entry.path) {
    const abs = path.isAbsolute(entry.path) ? entry.path : path.join(rootDir, entry.path);
    delete require.cache[require.resolve(abs)];
    return normalizePluginExport(require(abs));
  }
  if (entry.code) {
    const module = { exports: {} };
    const exports = module.exports;
    const req = (id) => {
      if (id.startsWith('.')) return require(path.resolve(rootDir, id));
      return require(id);
    };
    const __filename = path.join(rootDir, '__dynamic_plugin__.js');
    const __dirname = rootDir;
    eval('(function(module, exports, require, __dirname, __filename) { ' + entry.code + '\n})(module, exports, req, __dirname, __filename);');
    return normalizePluginExport(module.exports);
  }
  return null;
}

function buildPlugins(config, rootDir) {
  const list = [];
  for (const p of config.plugins || []) {
    const loaded = loadPluginEntry(p, rootDir);
    if (loaded) list.push(loaded);
  }
  return list;
}

function applyResponseIntercept(plugins, req, res) {
  const hasResponse = plugins.some((p) => p.response);
  if (!hasResponse) return;

  const chunks = [];
  const origWrite = res.write.bind(res);
  const origEnd = res.end.bind(res);
  let finished = false;

  res.write = function (chunk, encoding, cb) {
    if (chunk) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, encoding || 'utf8'));
    if (typeof cb === 'function') cb();
    return true;
  };

  res.end = function (chunk, encoding, cb) {
    if (finished) return res;
    finished = true;
    if (chunk) chunks.push(Buffer.isBuffer(chunk) ? chunk : Buffer.from(chunk, encoding || 'utf8'));

    const encodingArg = typeof encoding === 'function' ? null : encoding;
    const cbArg = typeof encoding === 'function' ? encoding : cb;

    (async () => {
      let body = Buffer.concat(chunks);
      let statusCode = res.statusCode;
      const headers = { ...res.getHeaders() };

      for (const pl of plugins) {
        if (!pl.response) continue;
        const out = await pl.response(req, res, { body, statusCode, headers });
        if (out && typeof out === 'object') {
          if (Buffer.isBuffer(out.body)) body = out.body;
          else if (typeof out.body === 'string') body = Buffer.from(out.body);
          else if (out.body != null) body = Buffer.from(String(out.body));
          if (typeof out.statusCode === 'number') statusCode = out.statusCode;
          if (out.headers && typeof out.headers === 'object') Object.assign(headers, out.headers);
        }
      }

      res.statusCode = statusCode;
      Object.keys(headers).forEach((k) => {
        try {
          res.setHeader(k, headers[k]);
        } catch (_) {}
      });
      origEnd.call(res, body, encodingArg, cbArg);
    })().catch((err) => {
      if (!res.headersSent) res.statusCode = 500;
      origEnd.call(res, Buffer.from(String(err && err.message ? err.message : err)), encodingArg, cbArg);
    });

    return res;
  };
}

function createGateway(config) {
  const app = express();
  const rootDir = path.dirname(fs.realpathSync(config.__configPath || __filename));
  const plugins = buildPlugins(config, rootDir);

  app.use((req, res, next) => {
    applyResponseIntercept(plugins, req, res);
    next();
  });

  app.use(express.json({ limit: '10mb' }));
  app.use(express.urlencoded({ extended: true, limit: '10mb' }));

  plugins.forEach((pl) => {
    if (pl.request) app.use(pl.request);
  });

  plugins.forEach((pl) => {
    if (pl.lifecycle) {
      app.use((req, res, next) => {
        try {
          const r = pl.lifecycle(req, res);
          if (r && typeof r.then === 'function') r.then(() => next()).catch(next);
          else next();
        } catch (e) {
          next(e);
        }
      });
    }
  });

  const target = config.target;
  app.use(
    '/',
    createProxyMiddleware({
      target,
      changeOrigin: true,
      ws: true,
      logLevel: 'warn',
    })
  );

  app.use((err, req, res, _next) => {
    if (res.headersSent) return;
    res.status(500).type('text').send(err && err.message ? err.message : String(err));
  });

  return app;
}

function main() {
  const configPath = process.env.GATEWAY_CONFIG || process.argv[2];
  const config = loadConfig();
  config.__configPath = configPath ? path.resolve(configPath) : __filename;

  const app = createGateway(config);
  const server = http.createServer(app);
  const port = config.port;
  server.listen(port, () => {
    process.stdout.write(`gateway listening on ${port} -> ${config.target}\n`);
  });
}

if (require.main === module) main();

module.exports = { loadConfig, createGateway, loadPluginEntry, buildPlugins };