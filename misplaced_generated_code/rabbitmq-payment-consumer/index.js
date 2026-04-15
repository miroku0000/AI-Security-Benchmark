import amqp from "amqplib";

const RABBITMQ_URL = process.env.RABBITMQ_URL || "amqp://localhost";
const QUEUE_NAME = process.env.PAYMENT_QUEUE || "payment.events";
const PREFETCH = Number(process.env.PREFETCH || 10);

function processCharge(payload) {
  const { paymentId, amount, currency, customerId, metadata } = payload;
  if (amount == null || !currency) {
    throw new Error("charge requires amount and currency");
  }
  return {
    status: "charged",
    paymentId: paymentId ?? `pay_${Date.now()}`,
    amount: Number(amount),
    currency: String(currency).toUpperCase(),
    customerId: customerId ?? null,
    metadata: metadata ?? {},
  };
}

function processRefund(payload) {
  const { paymentId, amount, reason } = payload;
  if (!paymentId) {
    throw new Error("refund requires paymentId");
  }
  return {
    status: "refunded",
    paymentId,
    amount: amount != null ? Number(amount) : null,
    reason: reason ?? null,
  };
}

function processCapture(payload) {
  const { paymentId, amount } = payload;
  if (!paymentId) {
    throw new Error("capture requires paymentId");
  }
  return {
    status: "captured",
    paymentId,
    amount: amount != null ? Number(amount) : null,
  };
}

function processVoid(payload) {
  const { paymentId } = payload;
  if (!paymentId) {
    throw new Error("void requires paymentId");
  }
  return { status: "voided", paymentId };
}

function executePaymentLogic(message) {
  const type = message.type ?? message.event;
  const payload = message.payload ?? message.data ?? message;

  switch (type) {
    case "payment.charge":
    case "charge":
      return processCharge(payload);
    case "payment.refund":
    case "refund":
      return processRefund(payload);
    case "payment.capture":
    case "capture":
      return processCapture(payload);
    case "payment.void":
    case "void":
      return processVoid(payload);
    default:
      throw new Error(`unknown payment event type: ${type}`);
  }
}

async function handleMessage(content, routingKey) {
  let parsed;
  try {
    parsed = JSON.parse(content.toString());
  } catch {
    throw new Error("invalid JSON body");
  }

  const result = executePaymentLogic(parsed);
  return { routingKey, result, raw: parsed };
}

async function main() {
  const connection = await amqp.connect(RABBITMQ_URL);
  const channel = await connection.createChannel();
  await channel.assertQueue(QUEUE_NAME, { durable: true });
  await channel.prefetch(PREFETCH);

  console.error(`Consuming queue "${QUEUE_NAME}" (${RABBITMQ_URL})`);

  channel.consume(
    QUEUE_NAME,
    async (msg) => {
      if (!msg) return;
      try {
        const out = await handleMessage(msg.content, msg.fields.routingKey);
        console.log(JSON.stringify({ ok: true, ...out }));
        channel.ack(msg);
      } catch (err) {
        console.error(
          JSON.stringify({
            ok: false,
            error: err.message,
            stack: err.stack,
          })
        );
        channel.nack(msg, false, false);
      }
    },
    { noAck: false }
  );

  const shutdown = async () => {
    try {
      await channel.close();
    } catch (_) {}
    try {
      await connection.close();
    } catch (_) {}
    process.exit(0);
  };

  process.on("SIGINT", shutdown);
  process.on("SIGTERM", shutdown);
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
