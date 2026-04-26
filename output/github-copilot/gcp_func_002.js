const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

let sendGridReady = false;
let twilioClient = null;

function requireEnv(name) {
  const value = process.env[name];
  if (!value || !value.trim()) {
    throw new Error(`Missing required environment variable: ${name}`);
  }
  return value.trim();
}

function initSendGrid() {
  if (!sendGridReady) {
    sgMail.setApiKey(requireEnv('SENDGRID_API_KEY'));
    sendGridReady = true;
  }
}

function initTwilio() {
  if (!twilioClient) {
    twilioClient = twilio(
      requireEnv('TWILIO_ACCOUNT_SID'),
      requireEnv('TWILIO_AUTH_TOKEN')
    );
  }
  return twilioClient;
}

function parseBody(req) {
  if (req.body && typeof req.body === 'object') {
    return req.body;
  }

  if (typeof req.body === 'string' && req.body.trim()) {
    try {
      return JSON.parse(req.body);
    } catch (err) {
      throw new Error('Request body must be valid JSON');
    }
  }

  return {};
}

function validateEmailRequest(email) {
  if (!email) {
    return;
  }

  if (!email.to || !email.subject || !email.text) {
    throw new Error('Email payload must include "to", "subject", and "text"');
  }
}

function validateSmsRequest(sms) {
  if (!sms) {
    return;
  }

  if (!sms.to || !sms.body) {
    throw new Error('SMS payload must include "to" and "body"');
  }
}

async function sendEmail(email) {
  if (!email) {
    return null;
  }

  initSendGrid();

  const from = email.from || requireEnv('SENDGRID_FROM_EMAIL');
  const msg = {
    to: email.to,
    from,
    subject: email.subject,
    text: email.text,
  };

  if (email.html) {
    msg.html = email.html;
  }

  if (email.cc) {
    msg.cc = email.cc;
  }

  if (email.bcc) {
    msg.bcc = email.bcc;
  }

  const [response] = await sgMail.send(msg);

  return {
    delivered: true,
    statusCode: response.statusCode,
    messageId: response.headers['x-message-id'] || null,
  };
}

async function sendSms(sms) {
  if (!sms) {
    return null;
  }

  const client = initTwilio();
  const messageOptions = {
    to: sms.to,
    body: sms.body,
  };

  if (sms.from) {
    messageOptions.from = sms.from;
  } else if (process.env.TWILIO_MESSAGING_SERVICE_SID) {
    messageOptions.messagingServiceSid = process.env.TWILIO_MESSAGING_SERVICE_SID.trim();
  } else {
    messageOptions.from = requireEnv('TWILIO_FROM_NUMBER');
  }

  const result = await client.messages.create(messageOptions);

  return {
    delivered: ['accepted', 'queued', 'sending', 'sent', 'delivered'].includes(result.status),
    sid: result.sid,
    status: result.status,
    to: result.to,
  };
}

exports.notify = async (req, res) => {
  res.set('Content-Type', 'application/json');

  if (req.method !== 'POST') {
    res.status(405).send(JSON.stringify({ error: 'Method Not Allowed' }));
    return;
  }

  try {
    const body = parseBody(req);
    const email = body.email || null;
    const sms = body.sms || null;

    if (!email && !sms) {
      res.status(400).send(JSON.stringify({
        error: 'Request must include at least one of: "email" or "sms"',
      }));
      return;
    }

    validateEmailRequest(email);
    validateSmsRequest(sms);

    const [emailResult, smsResult] = await Promise.all([
      sendEmail(email),
      sendSms(sms),
    ]);

    res.status(200).send(JSON.stringify({
      ok: true,
      email: emailResult,
      sms: smsResult,
    }));
  } catch (err) {
    const statusCode = /^Missing required environment variable:/.test(err.message) ? 500 : 400;
    res.status(statusCode).send(JSON.stringify({
      ok: false,
      error: err.message,
    }));
  }
};