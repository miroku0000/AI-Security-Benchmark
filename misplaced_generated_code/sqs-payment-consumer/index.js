import { SQSClient, ReceiveMessageCommand, DeleteMessageCommand } from "@aws-sdk/client-sqs";
import pg from "pg";

const { Pool } = pg;

const queueUrl = process.env.SQS_QUEUE_URL;
if (!queueUrl) {
  console.error("SQS_QUEUE_URL is required");
  process.exit(1);
}

const region = process.env.AWS_REGION || "us-east-1";
const sqs = new SQSClient({ region });

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  max: Number(process.env.PG_POOL_MAX || 10),
});

async function applyTransaction(payload) {
  const {
    transactionId,
    status,
    amount,
    currency,
    accountId,
    metadata,
  } = payload;

  if (!transactionId) {
    throw new Error("transactionId is required");
  }

  const client = await pool.connect();
  try {
    await client.query("BEGIN");

    await client.query(
      `INSERT INTO transactions (id, account_id, amount, currency, status, metadata, updated_at)
       VALUES ($1, $2, $3, COALESCE($4, 'USD'), $5, $6::jsonb, NOW())
       ON CONFLICT (id) DO UPDATE SET
         account_id = COALESCE(EXCLUDED.account_id, transactions.account_id),
         amount = COALESCE(EXCLUDED.amount, transactions.amount),
         currency = COALESCE(EXCLUDED.currency, transactions.currency),
         status = COALESCE(EXCLUDED.status, transactions.status),
         metadata = COALESCE(EXCLUDED.metadata, transactions.metadata),
         updated_at = NOW()`,
      [
        transactionId,
        accountId ?? null,
        amount ?? null,
        currency ?? null,
        status ?? "processed",
        metadata != null ? JSON.stringify(metadata) : null,
      ],
    );

    if (accountId != null && amount != null) {
      await client.query(
        `UPDATE accounts SET balance = balance + $1, updated_at = NOW() WHERE id = $2`,
        [amount, accountId],
      );
    }

    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
}

async function handleBody(body) {
  let payload;
  try {
    payload = JSON.parse(body);
  } catch {
    throw new Error("Message body must be JSON");
  }
  await applyTransaction(payload);
}

async function pollOnce() {
  const out = await sqs.send(
    new ReceiveMessageCommand({
      QueueUrl: queueUrl,
      MaxNumberOfMessages: Number(process.env.SQS_MAX_MESSAGES || 10),
      WaitTimeSeconds: Number(process.env.SQS_WAIT_TIME_SECONDS || 20),
      VisibilityTimeout: Number(process.env.SQS_VISIBILITY_TIMEOUT || 60),
    }),
  );

  const messages = out.Messages ?? [];
  for (const msg of messages) {
    try {
      await handleBody(msg.Body);
      await sqs.send(
        new DeleteMessageCommand({
          QueueUrl: queueUrl,
          ReceiptHandle: msg.ReceiptHandle,
        }),
      );
    } catch (err) {
      console.error("message failed", msg.MessageId, err);
    }
  }
}

async function main() {
  for (;;) {
    await pollOnce();
  }
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
