const crypto = require('crypto');
const AWS = require('aws-sdk');

const dynamo = new AWS.DynamoDB.DocumentClient();
const TABLE_NAME = process.env.USERS_TABLE_NAME || 'Users';

function validateEmail(email) {
  if (typeof email !== 'string') return false;
  const trimmed = email.trim();
  if (!trimmed) return false;
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(trimmed);
}

function validatePassword(password) {
  if (typeof password !== 'string') return false;
  return password.length >= 8 && password.length <= 128;
}

function hashPassword(password) {
  const salt = crypto.randomBytes(16).toString('hex');
  const iterations = 100000;
  const keylen = 64;
  const digest = 'sha512';
  const hash = crypto
    .pbkdf2Sync(password, salt, iterations, keylen, digest)
    .toString('hex');
  return {
    salt,
    hash,
    iterations,
    keylen,
    digest,
  };
}

function buildResponse(statusCode, body) {
  return {
    statusCode,
    headers: {
      'Content-Type': 'application/json',
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Headers': 'Content-Type',
      'Access-Control-Allow-Methods': 'OPTIONS,POST',
    },
    body: JSON.stringify(body),
  };
}

exports.handler = async (event) => {
  if (event.httpMethod === 'OPTIONS') {
    return buildResponse(204, {});
  }

  if (event.httpMethod !== 'POST') {
    return buildResponse(405, { message: 'Method not allowed' });
  }

  if (!event.body) {
    return buildResponse(400, { message: 'Request body is required' });
  }

  let payload;
  try {
    payload = JSON.parse(event.body);
  } catch (err) {
    return buildResponse(400, { message: 'Invalid JSON body' });
  }

  const { email, password } = payload || {};

  if (!validateEmail(email)) {
    return buildResponse(400, { message: 'Invalid email' });
  }

  if (!validatePassword(password)) {
    return buildResponse(400, {
      message: 'Invalid password (must be 8-128 characters)',
    });
  }

  const normalizedEmail = email.trim().toLowerCase();
  const passwordData = hashPassword(password);
  const now = new Date().toISOString();

  const userItem = {
    email: normalizedEmail,
    passwordHash: passwordData.hash,
    passwordSalt: passwordData.salt,
    passwordIterations: passwordData.iterations,
    passwordKeyLength: passwordData.keylen,
    passwordDigest: passwordData.digest,
    createdAt: now,
    updatedAt: now,
  };

  const params = {
    TableName: TABLE_NAME,
    Item: userItem,
    ConditionExpression: 'attribute_not_exists(email)',
  };

  try {
    await dynamo.put(params).promise();
    return buildResponse(201, {
      message: 'User registered successfully',
      email: normalizedEmail,
      createdAt: now,
    });
  } catch (err) {
    if (err && (err.code === 'ConditionalCheckFailedException')) {
      return buildResponse(409, { message: 'User already exists' });
    }

    console.error('Error creating user:', err);
    return buildResponse(500, { message: 'Internal server error' });
  }
};