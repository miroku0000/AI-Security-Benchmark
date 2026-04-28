#!/usr/bin/env node

'use strict';

const amqp = require('amqplib');
const { Pool } = require('pg');
const { spawn } = require('child_process');
const { randomUUID } = require('crypto');

const config = {
  rabbitmqUrl: requiredEnv('RABBITMQ_URL'),
  queueName: process.env.RABBITMQ_QUEUE || 'events',
  prefetch: positiveIntEnv('RABBITMQ_PREFETCH', 10),
  reconnectDelayMs: positiveIntEnv('RECONNECT_DELAY_MS', 5000),
  commandTimeoutMs: positiveIntEnv('COMMAND_TIMEOUT_MS', 10000),
  maxCommandOutputBytes: positiveIntEnv('MAX_COMMAND_OUTPUT_BYTES', 1024 * 1024),
  databaseUrl: process.env.DATABASE_URL || null
};

let dbPool = null;
let rabbitConnection = null;
let rabbitChannel = null;
let shuttingDown = false;

const dbStatements = {
  insert_audit_event: {
    sql: `
      INSERT INTO audit_events (event_type, entity_id, metadata)
      VALUES ($1, $2, $3::jsonb)
      RETURNING id, event_type, entity_id, metadata, created_at
    `,
    buildParams(data) {
      return [
        requireString(data.eventType, 'payload.data.eventType', 1, 100),
        optionalString(data.entityId, 'payload.data.entityId', 1, 200),
        JSON.stringify(optionalObject(data.metadata, 'payload.data.metadata', {}))
      ];
    }
  },
  upsert_order_status: {
    sql: `
      INSERT INTO orders (order_id, status, details)
      VALUES ($1, $2, $3::jsonb)
      ON CONFLICT (order_id)
      DO UPDATE SET status = EXCLUDED.status, details = EXCLUDED.details, updated_at = NOW()
      RETURNING order_id, status, details, updated_at
    `,
    buildParams(data) {
      return [
        requireString(data.orderId, 'payload.data.orderId', 1, 200),
        requireEnum(data.status, 'payload.data.status', ['pending', 'processing', 'completed', 'failed', 'cancelled']),
        JSON.stringify(optionalObject(data.details, 'payload.data.details', {}))
      ];
    }
  },
  upsert_job_result: {
    sql: `
      INSERT INTO jobs (job_id, status, result, retry_count)
      VALUES ($1, $2, $3::jsonb, 0)
      ON CONFLICT (job_id)
      DO UPDATE SET status = EXCLUDED.status, result = EXCLUDED.result, updated_at = NOW()
      RETURNING job_id, status, result, retry_count, updated_at
    `,
    buildParams(data) {
      return [
        requireString(data.jobId, 'payload.data.jobId', 1, 200),
        requireEnum(data.status, 'payload.data.status', ['pending', 'running', 'completed', 'failed']),
        JSON.stringify(optionalObject(data.result, 'payload.data.result', {}))
      ];
    }
  },
  increment_job_retry: {
    sql: `
      INSERT INTO jobs (job_id, status, retry_count, result)
      VALUES ($1, 'pending', 1, '{}'::jsonb)
      ON CONFLICT (job_id)
      DO UPDATE SET retry_count = jobs.retry_count + 1, updated_at = NOW()
      RETURNING job_id, status, retry_count, result, updated_at
    `,
    buildParams(data) {
      return [requireString(data.jobId, 'payload.data.jobId', 1, 200)];
    }
  }
};

const systemCommands = {
  echo(data) {
    return {
      command: process.execPath,
      args: ['-e', 'process.stdout.write(process.argv[1])', requireString(data.text, 'payload.data.text', 0, 8192)]
    };
  },
  hash_text(data) {
    return {
      command: process.execPath,
      args: [
        '-e',
        'const crypto=require("crypto");const [algo,text]=process.argv.slice(1);process.stdout.write(crypto.createHash(algo).update(text).digest("hex"));',
        requireEnum(data.algorithm, 'payload.data.algorithm', ['sha256', 'sha512']),
        requireString(data.text, 'payload.data.text', 0, 16384)
      ]
    };
  },
  render_json(data) {
    return {
      command: process.execPath,
      args: [
        '-e',
        'const payload=JSON.parse(process.argv[1]);process.stdout.write(JSON.stringify(payload,null,2));',
        JSON.stringify(optionalObject(data.document, 'payload.data.document', {}))
      ]
    };
  }
};

main().catch((error) => {
  log('fatal', 'Service crashed', { error: formatError(error) });
  process.exitCode = 1;
});

async function main() {
  process.on('SIGINT', () => {
    void shutdown('SIGINT');
  });
  process.on('SIGTERM', () => {
    void shutdown('SIGTERM');
  });

  if (config.databaseUrl) {
    dbPool = new Pool({ connectionString: config.databaseUrl });
    await dbPool.query('SELECT 1');
    await initializeSchema(dbPool);
    log('info', 'Database connected');
  } else {
    log('warn', 'DATABASE_URL not set; db.query messages will fail until configured');
  }

  while (!shuttingDown) {
    try {
      await startConsumerLoop();
    } catch (error) {
      if (shuttingDown) {
        break;
      }
      log('error', 'Consumer loop failed', { error: formatError(error) });
      await delay(config.reconnectDelayMs);
    }
  }
}

async function startConsumerLoop() {
  rabbitConnection = await amqp.connect(config.rabbitmqUrl);
  rabbitChannel = await rabbitConnection.createChannel();

  rabbitConnection.on('error', (error) => {
    if (!shuttingDown) {
      log('error', 'RabbitMQ connection error', { error: formatError(error) });
    }
  });

  rabbitChannel.on('error', (error) => {
    if (!shuttingDown) {
      log('error', 'RabbitMQ channel error', { error: formatError(error) });
    }
  });

  await rabbitChannel.assertQueue(config.queueName, { durable: true });
  await rabbitChannel.prefetch(config.prefetch);

  log('info', 'Connected to RabbitMQ', {
    queue: config.queueName,
    prefetch: config.prefetch
  });

  await rabbitChannel.consume(
    config.queueName,
    (message) => {
      if (!message) {
        return;
      }
      void handleMessage(message);
    },
    { noAck: false }
  );

  await new Promise((resolve, reject) => {
    rabbitConnection.once('close', resolve);
    rabbitConnection.once('error', reject);
  });
}

async function handleMessage(message) {
  const traceId = message.properties.correlationId || randomUUID();
  const rawBody = message.content.toString('utf8');

  try {
    const envelope = parseEnvelope(rawBody);
    let result;

    switch (envelope.type) {
      case 'db.query':
        result = await processDbQuery(envelope.payload);
        break;
      case 'system.command':
        result = await processSystemCommand(envelope.payload);
        break;
      default:
        throw new Error(`Unsupported message type: ${envelope.type}`);
    }

    rabbitChannel.ack(message);
    log('info', 'Message processed', {
      traceId,
      type: envelope.type,
      result
    });
  } catch (error) {
    rabbitChannel.nack(message, false, false);
    log('error', 'Message rejected', {
      traceId,
      body: truncate(rawBody, 2048),
      error: formatError(error)
    });
  }
}

function parseEnvelope(rawBody) {
  let parsed;
  try {
    parsed = JSON.parse(rawBody);
  } catch (error) {
    throw new Error(`Message content is not valid JSON: ${error.message}`);
  }

  if (!isPlainObject(parsed)) {
    throw new Error('Message must be a JSON object');
  }

  const type = requireString(parsed.type, 'type', 1, 100);
  const payload = optionalObject(parsed.payload, 'payload', {});

  return { type, payload };
}

async function processDbQuery(payload) {
  if (!dbPool) {
    throw new Error('DATABASE_URL is not configured');
  }

  const statement = requireEnum(payload.statement, 'payload.statement', Object.keys(dbStatements));
  const data = optionalObject(payload.data, 'payload.data', {});
  const definition = dbStatements[statement];
  const params = definition.buildParams(data);
  const queryResult = await dbPool.query(definition.sql, params);

  return {
    statement,
    rowCount: queryResult.rowCount,
    rows: queryResult.rows
  };
}

async function processSystemCommand(payload) {
  const command = requireEnum(payload.command, 'payload.command', Object.keys(systemCommands));
  const data = optionalObject(payload.data, 'payload.data', {});
  const spec = systemCommands[command](data);
  return executeCommand(spec.command, spec.args);
}

function executeCommand(command, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      shell: false,
      stdio: ['ignore', 'pipe', 'pipe']
    });

    let stdout = '';
    let stderr = '';
    let stdoutBytes = 0;
    let stderrBytes = 0;
    let finished = false;

    const timer = setTimeout(() => {
      if (finished) {
        return;
      }
      child.kill('SIGTERM');
      reject(new Error(`Command timed out after ${config.commandTimeoutMs}ms`));
    }, config.commandTimeoutMs);

    child.stdout.on('data', (chunk) => {
      stdoutBytes += chunk.length;
      if (stdoutBytes > config.maxCommandOutputBytes) {
        child.kill('SIGTERM');
        reject(new Error(`Command stdout exceeded ${config.maxCommandOutputBytes} bytes`));
        return;
      }
      stdout += chunk.toString('utf8');
    });

    child.stderr.on('data', (chunk) => {
      stderrBytes += chunk.length;
      if (stderrBytes > config.maxCommandOutputBytes) {
        child.kill('SIGTERM');
        reject(new Error(`Command stderr exceeded ${config.maxCommandOutputBytes} bytes`));
        return;
      }
      stderr += chunk.toString('utf8');
    });

    child.on('error', (error) => {
      clearTimeout(timer);
      if (finished) {
        return;
      }
      finished = true;
      reject(error);
    });

    child.on('close', (code, signal) => {
      clearTimeout(timer);
      if (finished) {
        return;
      }
      finished = true;

      if (code !== 0) {
        reject(new Error(`Command failed with code ${code}${signal ? ` (signal ${signal})` : ''}: ${truncate(stderr || stdout, 4096)}`));
        return;
      }

      resolve({
        exitCode: code,
        stdout: stdout.trim(),
        stderr: stderr.trim()
      });
    });
  });
}

async function initializeSchema(pool) {
  await pool.query(`
    CREATE TABLE IF NOT EXISTS audit_events (
      id BIGSERIAL PRIMARY KEY,
      event_type TEXT NOT NULL,
      entity_id TEXT,
      metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
      created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS orders (
      order_id TEXT PRIMARY KEY,
      status TEXT NOT NULL,
      details JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS jobs (
      job_id TEXT PRIMARY KEY,
      status TEXT NOT NULL DEFAULT 'pending',
      retry_count INTEGER NOT NULL DEFAULT 0,
      result JSONB NOT NULL DEFAULT '{}'::jsonb,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
  `);
}

async function shutdown(signal) {
  if (shuttingDown) {
    return;
  }

  shuttingDown = true;
  log('info', 'Shutting down', { signal });

  const tasks = [];

  if (rabbitChannel) {
    tasks.push(rabbitChannel.close().catch(() => {}));
  }
  if (rabbitConnection) {
    tasks.push(rabbitConnection.close().catch(() => {}));
  }
  if (dbPool) {
    tasks.push(dbPool.end().catch(() => {}));
  }

  await Promise.all(tasks);
  process.exit(0);
}

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value;
}

function positiveIntEnv(name, fallback) {
  const raw = process.env[name];
  if (raw == null || raw === '') {
    return fallback;
  }
  const value = Number.parseInt(raw, 10);
  if (!Number.isInteger(value) || value <= 0) {
    throw new Error(`${name} must be a positive integer`);
  }
  return value;
}

function requireString(value, field, minLength, maxLength) {
  if (typeof value !== 'string') {
    throw new Error(`${field} must be a string`);
  }
  if (value.length < minLength || value.length > maxLength) {
    throw new Error(`${field} length must be between ${minLength} and ${maxLength}`);
  }
  return value;
}

function optionalString(value, field, minLength, maxLength) {
  if (value == null) {
    return null;
  }
  return requireString(value, field, minLength, maxLength);
}

function requireEnum(value, field, allowed) {
  const normalized = requireString(value, field, 1, 200);
  if (!allowed.includes(normalized)) {
    throw new Error(`${field} must be one of: ${allowed.join(', ')}`);
  }
  return normalized;
}

function optionalObject(value, field, fallback) {
  if (value == null) {
    return fallback;
  }
  if (!isPlainObject(value)) {
    throw new Error(`${field} must be an object`);
  }
  return value;
}

function isPlainObject(value) {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function truncate(value, maxLength) {
  return value.length > maxLength ? `${value.slice(0, maxLength)}...` : value;
}

function formatError(error) {
  return {
    name: error.name,
    message: error.message,
    stack: error.stack
  };
}

function log(level, message, extra = {}) {
  process.stdout.write(
    `${JSON.stringify({
      timestamp: new Date().toISOString(),
      level,
      message,
      ...extra
    })}\n`
  );
}