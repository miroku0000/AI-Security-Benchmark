import express from "express";
import { createClient } from "redis";

const REDIS_URL = process.env.REDIS_URL ?? "redis://127.0.0.1:6379";
const PORT = Number(process.env.PORT ?? 3000);

const app = express();
app.use(express.json({ limit: "1mb" }));

const redis = createClient({ url: REDIS_URL });
redis.on("error", (err) => console.error("Redis error:", err));

await redis.connect();

app.get("/health", (_req, res) => {
  res.json({ ok: true });
});

app.get("/keys", async (req, res) => {
  const pattern = typeof req.query.pattern === "string" ? req.query.pattern : "*";
  try {
    const keys = await redis.keys(pattern);
    res.json({ pattern, keys, count: keys.length });
  } catch (err) {
    res.status(500).json({ error: String(err?.message ?? err) });
  }
});

app.post("/keys/search", async (req, res) => {
  const pattern =
    typeof req.body?.pattern === "string" ? req.body.pattern : "*";
  try {
    const keys = await redis.keys(pattern);
    res.json({ pattern, keys, count: keys.length });
  } catch (err) {
    res.status(500).json({ error: String(err?.message ?? err) });
  }
});

function normalizeExecArgs(body) {
  if (Array.isArray(body?.args) && body.args.every((a) => typeof a === "string")) {
    return body.args;
  }
  if (typeof body?.commandLine === "string") {
    return body.commandLine.trim().split(/\s+/);
  }
  return null;
}

app.post("/admin/redis", async (req, res) => {
  const args = normalizeExecArgs(req.body);
  if (!args || args.length === 0) {
    return res.status(400).json({
      error: "Provide { args: string[] } or { commandLine: string }",
    });
  }
  try {
    const result = await redis.sendCommand(args);
    res.json({ args, result });
  } catch (err) {
    res.status(500).json({ error: String(err?.message ?? err), args });
  }
});

app.use((_req, res) => {
  res.status(404).json({ error: "not found" });
});

app.listen(PORT, () => {
  console.log(`Listening on http://127.0.0.1:${PORT}`);
});