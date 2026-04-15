const { SQSClient, ReceiveMessageCommand, DeleteMessageCommand } = require("@aws-sdk/client-sqs");
const { Pool } = require("pg");

const sqsClient = new SQSClient({ region: process.env.AWS_REGION || "us-east-1" });
const QUEUE_URL = process.env.SQS_QUEUE_URL;

const db = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: 10,
  ssl: process.env.NODE_ENV === "production" ? { rejectUnauthorized: true } : undefined,
});

async function ensureSchema() {
  await db.query(`
    CREATE TABLE IF NOT EXISTS transactions (
      id SERIAL PRIMARY KEY,
      transaction_id VARCHAR(255) UNIQUE NOT NULL,
      account_id VARCHAR(255) NOT NULL,
      amount NUMERIC(15,2) NOT NULL,
      currency VARCHAR(3) NOT NULL DEFAULT 'USD',
      type VARCHAR(50) NOT NULL,
      status VARCHAR(50) NOT NULL DEFAULT 'pending',
      metadata JSONB,
      created_at TIMESTAMPTZ DEFAULT NOW(),
      processed_at TIMESTAMPTZ
    );
    CREATE TABLE IF NOT EXISTS processing_log (
      id SERIAL PRIMARY KEY,
      transaction_id VARCHAR(255) NOT NULL,
      status VARCHAR(50) NOT NULL,
      error_message TEXT,
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
  `);
}

async function processTransaction(message) {
  const body = JSON.parse(message.Body);
  const { transactionId, accountId, amount, currency, type, metadata } = body;

  if (!transactionId || !accountId || amount == null || !type) {
    throw new Error(`Invalid message: missing required fields. Got keys: ${Object.keys(body).join(", ")}`);
  }

  if (typeof amount !== "number" || !isFinite(amount) || amount <= 0) {
    throw new Error(`Invalid amount: ${amount}`);
  }

  const client = await db.connect();
  try {
    await client.query("BEGIN");

    // Idempotency check — SQS delivers at-least-once, duplicates WILL happen
    const existing = await client.query(
      "SELECT id, status FROM transactions WHERE transaction_id = $1",
      [transactionId]
    );

    if (existing.rows.length > 0) {
      await client.query("ROLLBACK");
      console.log(`Duplicate transaction ${transactionId} skipped (status: ${existing.rows[0].status})`);
      return { skipped: true, reason: "duplicate" };
    }

    await client.query(
      `INSERT INTO transactions (transaction_id, account_id, amount, currency, type, status, metadata, processed_at)
       VALUES ($1, $2, $3, $4, $5, 'completed', $6, NOW())`,
      [transactionId, accountId, amount, currency || "USD", type, metadata ? JSON.stringify(metadata) : null]
    );

    await client.query(
      "INSERT INTO processing_log (transaction_id, status) VALUES ($1, $2)",
      [transactionId, "completed"]
    );

    await client.query("COMMIT");
    console.log(`Transaction ${transactionId} processed: ${type} ${amount} ${currency || "USD"} for account ${accountId}`);
    return { skipped: false };
  } catch (err) {
    await client.query("ROLLBACK");
    await db.query(
      "INSERT INTO processing_log (transaction_id, status, error_message) VALUES ($1, $2, $3)",
      [transactionId || "unknown", "failed", err.message]
    );
    throw err;
  } finally {
    client.release();
  }
}

async function pollMessages() {
  const response = await sqsClient.send(new ReceiveMessageCommand({
    QueueUrl: QUEUE_URL,
    MaxNumberOfMessages: 10,
    WaitTimeSeconds: 20,
    MessageAttributeNames: ["All"],
  }));

  const messages = response.Messages || [];

  for (const message of messages) {
    try {
      await processTransaction(message);
      await sqsClient.send(new DeleteMessageCommand({
        QueueUrl: QUEUE_URL,
        ReceiptHandle: message.ReceiptHandle,
      }));
    } catch (err) {
      console.error(`Failed to process message ${message.MessageId}:`, err.message);
      // Message stays in queue and will be retried or sent to DLQ
    }
  }

  return messages.length;
}

let running = true;

async function main() {
  if (!QUEUE_URL) {
    console.error("SQS_QUEUE_URL environment variable is required");
    process.exit(1);
  }
  if (!process.env.DATABASE_URL) {
    console.error("DATABASE_URL environment variable is required");
    process.exit(1);
  }

  await ensureSchema();
  console.log("SQS transaction consumer started");

  while (running) {
    try {
      await pollMessages();
    } catch (err) {
      console.error("Poll error:", err.message);
      await new Promise((r) => setTimeout(r, 5000));
    }
  }

  await db.end();
}

process.on("SIGINT", () => { running = false; });
process.on("SIGTERM", () => { running = false; });

main().catch((err) => {
  console.error("Fatal:", err);
  process.exit(1);
});