const ddb = DynamoDBDocumentClient.from(new DynamoDBClient({}));
const paymentTimeoutMs = Number(PAYMENT_API_TIMEOUT_MS);
const maxConcurrency = Math.max(1, Number(MAX_CONCURRENCY) || 20);

async function callPaymentApi(order) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), paymentTimeoutMs);

  try {
    const response = await fetch(PAYMENT_API_URL, {
      method: 'POST',
      headers: {
        'content-type': 'application/json',
        authorization: `Bearer ${PAYMENT_API_KEY}`,
      },
      body: JSON.stringify({
        orderId: order.orderId,
        amount: order.amount,
        currency: order.currency,
        paymentMethod: order.paymentMethod,
        customerId: order.customerId,
      }),
      signal: controller.signal,
    });

    const text = await response.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { rawBody: text };
    }

    if (!response.ok) {
      const error = new Error(`Payment API request failed with status ${response.status}`);
      error.details = data;
      throw error;
    }

    return data;
  } finally {
    clearTimeout(timeout);
  }
}

async function updateOrder(order, paymentResult) {
  const now = new Date().toISOString();

  await ddb.send(
    new UpdateCommand({
      TableName: ORDERS_TABLE,
      Key: { orderId: order.orderId },
      UpdateExpression: `
        SET #status = :status,
            paymentStatus = :paymentStatus,
            paymentTransactionId = :paymentTransactionId,
            paymentResponse = :paymentResponse,
            updatedAt = :updatedAt
      `,
      ExpressionAttributeNames: {
        '#status': 'status',
      },
      ExpressionAttributeValues: {
        ':status': 'PAID',
        ':paymentStatus': paymentResult.status || 'APPROVED',
        ':paymentTransactionId': paymentResult.transactionId || paymentResult.id || null,
        ':paymentResponse': paymentResult,
        ':updatedAt': now,
      },
    })
  );
}

async function processRecord(record) {
  const order = JSON.parse(record.body);

  if (
    !order ||
    typeof order.orderId !== 'string' ||
    typeof order.amount !== 'number' ||
    typeof order.currency !== 'string'
  ) {
    throw new Error('Invalid order payload');
  }

  const paymentResult = await callPaymentApi(order);
  await updateOrder(order, paymentResult);
}

async function runWithConcurrency(items, worker, limit) {
  const failures = [];
  let index = 0;

  async function next() {
    while (true) {
      const current = index++;
      if (current >= items.length) return;

      const item = items[current];
      try {
        await worker(item);
      } catch (error) {
        console.error('Order processing failed', {
          messageId: item.messageId,
          error: error.message,
          stack: error.stack,
        });
        failures.push({ itemIdentifier: item.messageId });
      }
    }
  }

  const workers = Array.from({ length: Math.min(limit, items.length) }, () => next());
  await Promise.all(workers);

  return failures;
}

exports.handler = async (event) => {
  const records = Array.isArray(event?.Records) ? event.Records : [];
  const batchItemFailures = await runWithConcurrency(records, processRecord, maxConcurrency);
  return { batchItemFailures };
};