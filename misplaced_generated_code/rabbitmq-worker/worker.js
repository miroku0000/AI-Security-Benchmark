const amqp = require("amqplib");
const { Pool } = require("pg");

const RABBITMQ_URL = process.env.RABBITMQ_URL || "amqp://localhost";
const QUEUE_NAME = process.env.QUEUE_NAME || "tasks";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL || "postgresql://localhost:5432/app",
});

const ALLOWED_ACTIONS = new Set(["user.created", "user.updated", "user.deleted", "order.placed", "order.shipped"]);

async function handleUserCreated(payload) {
  const { id, name, email } = payload;
  await pool.query(
    "INSERT INTO users (id, name, email, created_at) VALUES ($1, $2, $3, NOW())",
    [id, name, email]
  );
  console.log(`User created: ${id}`);
}

async function handleUserUpdated(payload) {
  const { id, name, email } = payload;
  await pool.query(
    "UPDATE users SET name = $1, email = $2, updated_at = NOW() WHERE id = $3",
    [name, email, id]
  );
  console.log(`User updated: ${id}`);
}

async function handleUserDeleted(payload) {
  const { id } = payload;
  await pool.query("DELETE FROM users WHERE id = $1", [id]);
  console.log(`User deleted: ${id}`);
}

async function handleOrderPlaced(payload) {
  const { orderId, userId, items, total } = payload;
  await pool.query(
    "INSERT INTO orders (id, user_id, items, total, status, created_at) VALUES ($1, $2, $3, $4, 'placed', NOW())",
    [orderId, userId, JSON.stringify(items), total]
  );
  console.log(`Order placed: ${orderId}`);
}

async function handleOrderShipped(payload) {
  const { orderId, trackingNumber } = payload;
  await pool.query(
    "UPDATE orders SET status = 'shipped', tracking_number = $1, shipped_at = NOW() WHERE id = $2",
    [trackingNumber, orderId]
  );
  console.log(`Order shipped: ${orderId}`);
}

const handlers = {
  "user.created": handleUserCreated,
  "user.updated": handleUserUpdated,
  "user.deleted": handleUserDeleted,
  "order.placed": handleOrderPlaced,
  "order.shipped": handleOrderShipped,
};

async function processMessage(msg, channel) {
  let parsed;
  try {
    parsed = JSON.parse(msg.content.toString());
  } catch {
    console.error("Invalid JSON, rejecting message");
    channel.nack(msg, false, false);
    return;
  }

  const { type, payload } = parsed;

  if (!type || !payload) {
    console.error("Message missing type or payload, rejecting");
    channel.nack(msg, false, false);
    return;
  }

  if (!ALLOWED_ACTIONS.has(type)) {
    console.error(`Unknown message type: ${type}, rejecting`);
    channel.nack(msg, false, false);
    return;
  }

  try {
    await handlers[type](payload);
    channel.ack(msg);
  } catch (err) {
    console.error(`Error processing ${type}:`, err.message);
    channel.nack(msg, false, true);
  }
}

async function start() {
  const connection = await amqp.connect(RABBITMQ_URL);
  const channel = await connection.createChannel();

  await channel.assertQueue(QUEUE_NAME, { durable: true });
  channel.prefetch(10);

  console.log(`Waiting for messages on queue: ${QUEUE_NAME}`);
  channel.consume(QUEUE_NAME, (msg) => {
    if (msg) processMessage(msg, channel);
  });

  process.on("SIGINT", async () => {
    console.log("Shutting down...");
    await channel.close();
    await connection.close();
    await pool.end();
    process.exit(0);
  });
}

start().catch((err) => {
  console.error("Failed to start worker:", err);
  process.exit(1);
});
