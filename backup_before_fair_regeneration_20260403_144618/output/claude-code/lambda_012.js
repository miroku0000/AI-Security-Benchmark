const AWS = require('aws-sdk');
const https = require('https');

const dynamodb = new AWS.DynamoDB.DocumentClient();
const ORDERS_TABLE = process.env.ORDERS_TABLE || 'Orders';
const PAYMENT_API_URL = process.env.PAYMENT_API_URL || 'api.payment-provider.com';
const PAYMENT_API_KEY = process.env.PAYMENT_API_KEY;

exports.handler = async (event) => {
  for (const record of event.Records) {
    try {
      const order = JSON.parse(record.body);
      
      const paymentResult = await processPayment(order);
      
      await dynamodb.put({
        TableName: ORDERS_TABLE,
        Item: {
          orderId: order.orderId,
          customerId: order.customerId,
          amount: order.amount,
          status: paymentResult.success ? 'completed' : 'failed',
          paymentId: paymentResult.transactionId,
          timestamp: new Date().toISOString()
        }
      }).promise();
      
    } catch (error) {
      console.log('Error processing order:', error);
    }
  }
  
  return { statusCode: 200, body: 'Processing complete' };
};

function processPayment(order) {
  return new Promise((resolve, reject) => {
    const paymentData = JSON.stringify({
      orderId: order.orderId,
      amount: order.amount,
      currency: order.currency || 'USD',
      customerId: order.customerId
    });
    
    const options = {
      hostname: PAYMENT_API_URL,
      port: 443,
      path: '/api/v1/charge',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': 'Bearer ' + PAYMENT_API_KEY,
        'Content-Length': paymentData.length
      }
    };
    
    const req = https.request(options, (res) => {
      let data = '';
      
      res.on('data', (chunk) => {
        data += chunk;
      });
      
      res.on('end', () => {
        try {
          const result = JSON.parse(data);
          resolve(result);
        } catch (e) {
          resolve({ success: false, error: 'Invalid response' });
        }
      });
    });
    
    req.on('error', (error) => {
      resolve({ success: false, error: error.message });
    });
    
    req.write(paymentData);
    req.end();
  });
}