const { DynamoDBClient } = require("@aws-sdk/client-dynamodb");
const { DynamoDBDocumentClient, UpdateCommand } = require("@aws-sdk/lib-dynamodb");

const dynamo = DynamoDBDocumentClient.from(new DynamoDBClient({}));

const PAYMENT_API_URL = process.env.PAYMENT_API_URL;
const PAYMENT_API_KEY = process.env.PAYMENT_API_KEY;
const ORDERS_TABLE_NAME = process.env.ORDERS_TABLE_NAME;

async function callPaymentApi(order) {
  const res = await fetch(PAYMENT_API_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${PAYMENT_API_KEY}`,
    },
    body: JSON.stringify({
      orderId: order.orderId,
      amount: order.amount,
      currency: order.currency,
    }),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Payment API error ${res.status}: ${text}`);
  }
  return res.json();
}

async function updateOrderInDynamoDB(orderId, paymentResult) {
  await dynamo.send(
    new UpdateCommand({
      TableName: ORDERS_TABLE_NAME,
      Key: { orderId },
      UpdateExpression:
        "SET #st = :status, paymentRef = :ref, updatedAt = :ua",
      ExpressionAttributeNames: { "#st": "status" },
      ExpressionAttributeValues: {
        ":status": paymentResult.status || "processed",
        ":ref": paymentResult.reference || paymentResult.id || "",
        ":ua": new Date().toISOString(),
      },
    })
  );
}

async function processRecord(record) {
  const order = JSON.parse(record.body);
  const paymentResult = await callPaymentApi(order);
  await updateOrderInDynamoDB(order.orderId, paymentResult);
}

exports.handler = async (event) => {
  await Promise.all(
    event.Records.map(async (record) => {
      try {
        await processRecord(record);
      } catch (err) {
        console.error(
          JSON.stringify({
            message: err.message,
            stack: err.stack,
            messageId: record.messageId,
          })
        );
      }
    })
  );
};