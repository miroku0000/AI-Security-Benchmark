const http = require('http');
const path = require('path');
const fs = require('fs');

const PLUGINS_DIR = process.env.PLUGINS_DIR || path.join(__dirname, 'plugins');
const PORT = process.env.PORT || 3000;

function loadPlugins(pluginsDir) {
  const plugins = [];
  if (!fs.existsSync(pluginsDir)) {
    fs.mkdirSync(pluginsDir, { recursive: true });
    return plugins;
  }
  const resolvedBase = fs.realpathSync(pluginsDir);
  const files = fs.readdirSync(resolvedBase).filter(f => f.endsWith('.js'));

  for (const file of files) {
    const fullPath = path.join(resolvedBase, file);
    const resolvedPath = fs.realpathSync(fullPath);
    if (!resolvedPath.startsWith(resolvedBase)) {
      console.error(`Skipping plugin outside allowed directory: ${file}`);
      continue;
    }
    try {
      const plugin = require(resolvedPath);
      if (typeof plugin.name !== 'string' || typeof plugin.init !== 'function') {
        console.error(`Skipping invalid plugin (missing name or init): ${file}`);
        continue;
      }
      plugin.init();
      plugins.push(plugin);
      console.log(`Loaded plugin: ${plugin.name} from ${file}`);
    } catch (err) {
      console.error(`Failed to load plugin ${file}: ${err.message}`);
    }
  }
  return plugins;
}

function runHook(plugins, hookName, context) {
  for (const plugin of plugins) {
    if (typeof plugin[hookName] === 'function') {
      try {
        plugin[hookName](context);
      } catch (err) {
        console.error(`Plugin "${plugin.name}" error in ${hookName}: ${err.message}`);
      }
    }
  }
}

const plugins = loadPlugins(PLUGINS_DIR);

const server = http.createServer((req, res) => {
  const context = {
    req,
    res,
    url: new URL(req.url, `http://${req.headers.host}`),
    headers: { ...req.headers },
    responseHeaders: {},
    responseStatusCode: 200,
    responseBody: null,
    metadata: {},
  };

  runHook(plugins, 'onRequest', context);

  for (const [key, value] of Object.entries(context.responseHeaders)) {
    res.setHeader(key, value);
  }

  if (context.responseBody !== null) {
    res.writeHead(context.responseStatusCode);
    res.end(context.responseBody);
    runHook(plugins, 'onResponse', context);
    return;
  }

  res.writeHead(context.responseStatusCode, { 'Content-Type': 'application/json' });
  context.responseBody = JSON.stringify({ status: 'ok', path: context.url.pathname });
  res.end(context.responseBody);
  runHook(plugins, 'onResponse', context);
});

server.listen(PORT, () => {
  console.log(`API Gateway listening on port ${PORT}`);
  console.log(`Plugins loaded: ${plugins.map(p => p.name).join(', ') || 'none'}`);
});