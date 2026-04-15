import amqp from "amqplib";
import pg from "pg";
import { spawn } from "node:child_process";

const {
  RABBITMQ_URL = "amqp://localhost",
  QUEUE_NAME = "events",
  DATABASE_URL,
  PREFETCH = "10",
  ALLOWED_COMMANDS = "uptime,hostname,date",
} = process.env;

const ALLOWLIST = new Set(
  ALLOWED_COMMANDS.split(",")
    .map((s) => s.trim())
    .filter(Boolean)
);

const pool = DATABASE_URL
  ? new pg.Pool({ connectionString: DATABASE_URL })
  : null;

function parseMessageContent(buf) {
  const text = buf.toString("utf8").trim();
  if (!text) throw new Error("empty message body");
  try {
    return JSON.parse(text);
  } catch (e) {
    throw new Error(`invalid JSON: ${e.message}`);
  }
}

function validateEnvelope(msg) {
  if (!msg || typeof msg !== "object") throw new Error("message must be an object");
  if (typeof msg.type !== "string" || !msg.type) throw new Error("missing or invalid type");
  if (!("payload" in msg)) throw new Error("missing payload");
  return msg;
}

async function handleDatabaseQuery(payload) {
  if (!pool) throw new Error("DATABASE_URL not configured");
  const sql = payload?.sql;
  const params = Array.isArray(payload?.params) ? payload.params : [];
  if (typeof sql !== "string" || !sql.trim()) throw new Error("payload.sql required");
  const client = await pool.connect();
  try {
    const result = await client.query(sql, params);
    return { rows: result.rows, rowCount: result.rowCount, fields: result.fields?.map((f) => f.name) };
  } finally {
    client.release();
  }
}

async function handleDatabaseExecute(payload) {
  if (!pool) throw new Error("DATABASE_URL not configured");
  const sql = payload?.sql;
  const params = Array.isArray(payload?.params) ? payload.params : [];
  if (typeof sql !== "string" || !sql.trim()) throw new Error("payload.sql required");
  const client = await pool.connect();
  try {
    const result = await client.query(sql, params);
    return { rowCount: result.rowCount, command: result.command };
  } finally {
    client.release();
  }
}

function runAllowlistedCommand(payload) {
  const cmd = payload?.command;
  const args = Array.isArray(payload?.args) ? payload.args.map(String) : [];
  if (typeof cmd !== "string" || !cmd) throw new Error("payload.command required");
  if (!ALLOWLIST.has(cmd)) throw new Error(`command not allowlisted: ${cmd}`);
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, {
      shell: false,
      env: process.env,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (d) => {
      stdout += d.toString();
    });
    child.stderr.on("data", (d) => {
      stderr += d.toString();
    });
    child.on("error", reject);
    child.on("close", (code) => {
      resolve({ exitCode: code, stdout: stdout.trimEnd(), stderr: stderr.trimEnd() });
    });
  });
}

async function dispatch(type, payload) {
  switch (type) {
    case "database.query":
      return handleDatabaseQuery(payload);
    case "database.execute":
      return handleDatabaseExecute(payload);
    case "system.command":
      return runAllowlistedCommand(payload);
    case "noop":
      return { ok: true };
    default:
      throw new Error(`unknown message type: ${type}`);
  }
}

async function main() {
  const conn = await amqp.connect(RABBITMQ_URL);
  conn.on("error", (err) => {
    console.error("AMQP connection error", err);
  });
  const ch = await conn.createChannel();
  await ch.assertQueue(QUEUE_NAME, { durable: true });
  await ch.prefetch(Number(PREFETCH) || 10);

  console.log(`Consuming queue "${QUEUE_NAME}"`);

  ch.consume(
    QUEUE_NAME,
    async (msg) => {
      if (!msg) return;
      const deliveryTag = msg.fields.deliveryTag;
      try {
        const raw = parseMessageContent(msg.content);
        const envelope = validateEnvelope(raw);
        const result = await dispatch(envelope.type, envelope.payload);
        console.log(
          JSON.stringify({
            ok: true,
            deliveryTag,
            type: envelope.type,
            correlationId: envelope.correlationId ?? null,
            result,
          })
        );
        ch.ack(msg);
      } catch (err) {
        console.error(
          JSON.stringify({
            ok: false,
            deliveryTag,
            error: err.message,
          })
        );
        ch.nack(msg, false, false);
      }
    },
    { noAck: false }
  );

  const shutdown = async () => {
    try {
      await ch.close();
    } catch (_) {}
    try {
      await conn.close();
    } catch (_) {}
    if (pool) await pool.end();
    process.exit(0);
  };
  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
