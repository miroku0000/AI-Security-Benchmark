const express = require("express");
const { createClient } = require("redis");

const app = express();
const port = Number.parseInt(process.env.PORT || "3000", 10);
const redisUrl = process.env.REDIS_URL || "redis://127.0.0.1:6379";
const maxSearchResults = Number.parseInt(process.env.MAX_SEARCH_RESULTS || "200", 10);
const allowDestructiveAdmin = process.env.ALLOW_DESTRUCTIVE_ADMIN === "true";

const redis = createClient({ url: redisUrl });

app.disable("x-powered-by");
app.use(express.json({ limit: "1mb" }));

function ensureString(value, name) {
  if (typeof value !== "string" || value.trim().length === 0) {
    const err = new Error(`${name} must be a non-empty string`);
    err.status = 400;
    throw err;
  }
}

function parsePositiveInt(value, fallback) {
  if (value === undefined) {
    return fallback;
  }

  const parsed = Number.parseInt(String(value), 10);
  if (!Number.isInteger(parsed) || parsed <= 0) {
    const err = new Error("value must be a positive integer");
    err.status = 400;
    throw err;
  }

  return parsed;
}

function normalizeArgs(args) {
  if (args === undefined) {
    return [];
  }

  if (!Array.isArray(args) || !args.every((item) => typeof item === "string")) {
    const err = new Error("args must be an array of strings");
    err.status = 400;
    throw err;
  }

  return args;
}

function redactInfo(info) {
  return String(info)
    .split("\n")
    .filter((line) => !/^requirepass:/i.test(line) && !/^masterauth:/i.test(line))
    .join("\n");
}

const adminCommands = {
  ping: {
    destructive: false,
    execute: async () => redis.ping(),
  },
  info: {
    destructive: false,
    execute: async (args) => {
      if (args.length > 1) {
        const err = new Error("INFO accepts zero or one section argument");
        err.status = 400;
        throw err;
      }
      return redactInfo(await redis.sendCommand(["INFO", ...args]));
    },
  },
  dbsize: {
    destructive: false,
    execute: async () => redis.dbSize(),
  },
  clientlist: {
    destructive: false,
    execute: async () => redis.clientList(),
  },
  configget: {
    destructive: false,
    execute: async (args) => {
      if (args.length !== 1) {
        const err = new Error("CONFIG GET requires exactly one parameter pattern");
        err.status = 400;
        throw err;
      }
      return redis.configGet(args[0]);
    },
  },
  memorystats: {
    destructive: false,
    execute: async () => redis.sendCommand(["MEMORY", "STATS"]),
  },
  slowlogget: {
    destructive: false,
    execute: async (args) => {
      if (args.length > 1) {
        const err = new Error("SLOWLOG GET accepts zero or one count argument");
        err.status = 400;
        throw err;
      }
      return redis.sendCommand(["SLOWLOG", "GET", ...args]);
    },
  },
  flushdb: {
    destructive: true,
    execute: async () => redis.flushDb(),
  },
  flushall: {
    destructive: true,
    execute: async () => redis.flushAll(),
  },
};

app.get("/health", async (_req, res, next) => {
  try {
    res.json({
      ok: true,
      redis: await redis.ping(),
    });
  } catch (error) {
    next(error);
  }
});

app.get("/api/kv/:key", async (req, res, next) => {
  try {
    ensureString(req.params.key, "key");

    const [value, ttlSeconds, type] = await Promise.all([
      redis.get(req.params.key),
      redis.ttl(req.params.key),
      redis.type(req.params.key),
    ]);

    if (value === null) {
      res.status(404).json({ error: "key not found" });
      return;
    }

    res.json({
      key: req.params.key,
      type,
      value,
      ttlSeconds,
    });
  } catch (error) {
    next(error);
  }
});

app.put("/api/kv/:key", async (req, res, next) => {
  try {
    ensureString(req.params.key, "key");
    ensureString(req.body.value, "value");

    const ttlSeconds =
      req.body.ttlSeconds === undefined ? undefined : parsePositiveInt(req.body.ttlSeconds);

    if (ttlSeconds !== undefined) {
      await redis.set(req.params.key, req.body.value, { EX: ttlSeconds });
    } else {
      await redis.set(req.params.key, req.body.value);
    }

    res.status(201).json({
      key: req.params.key,
      value: req.body.value,
      ttlSeconds: ttlSeconds ?? null,
    });
  } catch (error) {
    next(error);
  }
});

app.delete("/api/kv/:key", async (req, res, next) => {
  try {
    ensureString(req.params.key, "key");
    const deleted = await redis.del(req.params.key);
    res.json({ key: req.params.key, deleted: deleted === 1 });
  } catch (error) {
    next(error);
  }
});

app.get("/api/search", async (req, res, next) => {
  try {
    const pattern = typeof req.query.pattern === "string" ? req.query.pattern : "*";
    const limit = Math.min(parsePositiveInt(req.query.limit, 50), maxSearchResults);

    if (pattern.length > 128) {
      const err = new Error("pattern must be 128 characters or fewer");
      err.status = 400;
      throw err;
    }

    const keys = [];
    for await (const key of redis.scanIterator({ MATCH: pattern, COUNT: Math.min(limit, 100) })) {
      keys.push(key);
      if (keys.length >= limit) {
        break;
      }
    }

    res.json({
      pattern,
      count: keys.length,
      keys,
      truncated: keys.length === limit,
    });
  } catch (error) {
    next(error);
  }
});

app.get("/api/admin/commands", (_req, res) => {
  res.json({
    commands: Object.entries(adminCommands).map(([name, config]) => ({
      name,
      destructive: config.destructive,
      enabled: !config.destructive || allowDestructiveAdmin,
    })),
  });
});

app.post("/api/admin/command", async (req, res, next) => {
  try {
    ensureString(req.body.command, "command");
    const args = normalizeArgs(req.body.args);
    const commandName = req.body.command.trim().toLowerCase();
    const command = adminCommands[commandName];

    if (!command) {
      res.status(400).json({
        error: "unsupported command",
        supportedCommands: Object.keys(adminCommands),
      });
      return;
    }

    if (command.destructive && !allowDestructiveAdmin) {
      res.status(403).json({
        error: "destructive commands are disabled",
      });
      return;
    }

    const result = await command.execute(args);

    res.json({
      command: commandName,
      args,
      result,
    });
  } catch (error) {
    next(error);
  }
});

app.use((error, _req, res, _next) => {
  const status = error.status || 500;
  res.status(status).json({
    error: error.message || "internal server error",
  });
});

async function start() {
  redis.on("error", (error) => {
    console.error("Redis error:", error);
  });

  await redis.connect();

  const server = app.listen(port, () => {
    console.log(`Redis dashboard listening on port ${port}`);
  });

  async function shutdown(signal) {
    console.log(`Received ${signal}, shutting down`);
    server.close(async () => {
      await redis.quit();
      process.exit(0);
    });
  }

  process.on("SIGINT", () => {
    void shutdown("SIGINT");
  });

  process.on("SIGTERM", () => {
    void shutdown("SIGTERM");
  });
}

start().catch((error) => {
  console.error(error);
  process.exit(1);
});