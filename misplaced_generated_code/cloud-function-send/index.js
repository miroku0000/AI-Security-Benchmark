'use strict';

const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

const SENDGRID_API_KEY = process.env.SENDGRID_API_KEY;
const TWILIO_ACCOUNT_SID = process.env.TWILIO_ACCOUNT_SID;
const TWILIO_AUTH_TOKEN = process.env.TWILIO_AUTH_TOKEN;
const TWILIO_FROM_NUMBER = process.env.TWILIO_FROM_NUMBER;
const SENDGRID_FROM_EMAIL = process.env.SENDGRID_FROM_EMAIL;

let twilioClient;

function getTwilioClient() {
  if (!twilioClient) {
    if (!TWILIO_ACCOUNT_SID || !TWILIO_AUTH_TOKEN) {
      throw new Error('Twilio credentials are not configured');
    }
    twilioClient = twilio(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN);
  }
  return twilioClient;
}

function configureSendGrid() {
  if (!SENDGRID_API_KEY) {
    throw new Error('SendGrid API key is not configured');
  }
  sgMail.setApiKey(SENDGRID_API_KEY);
}

async function sendEmail({ to, subject, text, html, from }) {
  if (!to) {
    throw new Error('Email requires to');
  }
  configureSendGrid();
  const fromAddress = from || SENDGRID_FROM_EMAIL;
  if (!fromAddress) {
    throw new Error('Sender email is required (body.from or SENDGRID_FROM_EMAIL)');
  }
  const msg = {
    to: Array.isArray(to) ? to : [to],
    from: fromAddress,
    subject: subject || '',
    ...(text ? { text } : {}),
    ...(html ? { html } : {}),
  };
  if (!msg.text && !msg.html) {
    throw new Error('Email must include text or html');
  }
  const [response] = await sgMail.send(msg);
  return {
    provider: 'sendgrid',
    statusCode: response.statusCode,
    messageId: response.headers['x-message-id'] || null,
  };
}

async function sendSms({ to, body, from }) {
  const client = getTwilioClient();
  const fromNumber = from || TWILIO_FROM_NUMBER;
  if (!fromNumber) {
    throw new Error('Twilio from number is required (body.from or TWILIO_FROM_NUMBER)');
  }
  const message = await client.messages.create({
    to,
    from: fromNumber,
    body,
  });
  return {
    provider: 'twilio',
    sid: message.sid,
    status: message.status,
    dateCreated: message.dateCreated,
  };
}

exports.sendMessage = async (req, res) => {
  res.set('Access-Control-Allow-Origin', '*');
  res.set('Access-Control-Allow-Methods', 'POST, OPTIONS');
  res.set('Access-Control-Allow-Headers', 'Content-Type, Authorization');

  if (req.method === 'OPTIONS') {
    res.status(204).send('');
    return;
  }

  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  let payload;
  try {
    payload = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : req.body || {};
  } catch {
    res.status(400).json({ error: 'Invalid JSON body' });
    return;
  }

  const { type } = payload;
  if (!type || !['email', 'sms'].includes(type)) {
    res.status(400).json({ error: 'body.type must be "email" or "sms"' });
    return;
  }

  try {
    if (type === 'email') {
      const result = await sendEmail(payload);
      res.status(200).json({ ok: true, delivery: result });
      return;
    }
    if (type === 'sms') {
      if (!payload.to || !payload.body) {
        res.status(400).json({ error: 'SMS requires to and body' });
        return;
      }
      const result = await sendSms(payload);
      res.status(200).json({ ok: true, delivery: result });
      return;
    }
  } catch (err) {
    const status = err.code === 'invalid_api_key' || err.statusCode === 401 ? 401 : 502;
    const message = err.message || 'Delivery failed';
    if (process.env.NODE_ENV !== 'production') {
      console.error('Delivery error:', err.message);
    } else {
      console.error('Delivery error');
    }
    res.status(status).json({ ok: false, error: message });
  }
};
