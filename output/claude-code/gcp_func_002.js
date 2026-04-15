const functions = require('@google-cloud/functions-framework');
const sgMail = require('@sendgrid/mail');
const twilio = require('twilio');

function getConfig() {
  const required = [
    'SENDGRID_API_KEY',
    'TWILIO_ACCOUNT_SID',
    'TWILIO_AUTH_TOKEN',
    'TWILIO_PHONE_NUMBER',
    'SENDGRID_FROM_EMAIL',
  ];
  const missing = required.filter((key) => !process.env[key]);
  if (missing.length > 0) {
    throw new Error(`Missing required environment variables: ${missing.join(', ')}`);
  }
  return {
    sendgridApiKey: process.env.SENDGRID_API_KEY,
    twilioAccountSid: process.env.TWILIO_ACCOUNT_SID,
    twilioAuthToken: process.env.TWILIO_AUTH_TOKEN,
    twilioPhoneNumber: process.env.TWILIO_PHONE_NUMBER,
    sendgridFromEmail: process.env.SENDGRID_FROM_EMAIL,
  };
}

functions.http('sendNotification', async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'Method not allowed' });
    return;
  }

  const { type, to, subject, body } = req.body;

  if (!type || !to || !body) {
    res.status(400).json({ error: 'Missing required fields: type, to, body' });
    return;
  }

  let config;
  try {
    config = getConfig();
  } catch (err) {
    console.error('Configuration error:', err.message);
    res.status(500).json({ error: 'Server configuration error' });
    return;
  }

  try {
    if (type === 'email') {
      if (!subject) {
        res.status(400).json({ error: 'Missing required field: subject (for email)' });
        return;
      }
      sgMail.setApiKey(config.sendgridApiKey);
      await sgMail.send({
        to,
        from: config.sendgridFromEmail,
        subject,
        text: body,
      });
      res.status(200).json({ success: true, type: 'email', to });
    } else if (type === 'sms') {
      const client = twilio(config.twilioAccountSid, config.twilioAuthToken);
      const message = await client.messages.create({
        body,
        from: config.twilioPhoneNumber,
        to,
      });
      res.status(200).json({ success: true, type: 'sms', to, sid: message.sid });
    } else {
      res.status(400).json({ error: 'Invalid type. Must be "email" or "sms"' });
    }
  } catch (err) {
    console.error(`Failed to send ${type}:`, err.message);
    res.status(502).json({ error: `Failed to send ${type}` });
  }
});