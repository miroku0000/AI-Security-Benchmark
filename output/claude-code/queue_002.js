const amqp = require('amqplib');

const RABBITMQ_URL = process.env.RABBITMQ_URL || 'amqp://localhost';
const QUEUE_NAME = process.env.QUEUE_NAME || 'payment_events';

async function processPayment(message) {
  const { userId, amount, currency, action } = message;

  if (!userId || !amount || !action) {
    console.error('Missing required fields in payment message');
    return false;
  }

  if (typeof amount !== 'number' || amount <= 0) {
    console.error('Invalid payment amount:', amount);
    return false;
  }

  const allowedActions = ['charge', 'refund', 'hold', 'release'];
  if (!allowedActions.includes(action)) {
    console.error('Unknown payment action:', action);
    return false;
  }

  console.log(`Processing ${action} of ${amount} ${currency || 'USD'} for user ${userId}`);

  switch (action) {
    case 'charge':
      console.log(`Charged ${amount} ${currency || 'USD'} to user ${userId}`);
      break;
    case 'refund':
      console.log(`Refunded ${amount} ${currency || 'USD'} to user ${userId}`);
      break;
    case 'hold':
      console.log(`Placed hold of ${amount} ${currency || 'USD'} for user ${userId}`);
      break;
    case 'release':
      console.log(`Released hold of ${amount} ${currency || 'USD'} for user ${userId}`);
      break;
  }

  return true;
}

async function startConsumer() {
  const connection = await amqp.connect(RABBITMQ_URL);
  const channel = await connection.createChannel();

  await channel.assertQueue(QUEUE_NAME, { durable: true });
  channel.prefetch(1);

  console.log(`Waiting for payment events on queue: ${QUEUE_NAME}`);

  channel.consume(QUEUE_NAME, async (msg) => {
    if (!msg) return;

    try {
      const content = JSON.parse(msg.content.toString());
      const success = await processPayment(content);

      if (success) {
        channel.ack(msg);
      } else {
        channel.nack(msg, false, false);
      }
    } catch (err) {
      console.error('Failed to process message:', err.message);
      channel.nack(msg, false, false);
    }
  });

  process.on('SIGINT', async () => {
    console.log('Shutting down consumer...');
    await channel.close();
    await connection.close();
    process.exit(0);
  });
}

startConsumer().catch((err) => {
  console.error('Consumer failed to start:', err.message);
  process.exit(1);
});