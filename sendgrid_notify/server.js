'use strict';

const express = require('express');
const sgMail = require('@sendgrid/mail');

const SENDGRID_API_KEY = 'SG.test_key_abc123';
const PORT = process.env.PORT || 3000;

sgMail.setApiKey(SENDGRID_API_KEY);

const app = express();
app.use(express.json());

function sendEmailNotification({ to, from, subject, text, html }) {
  if (!to || !subject || (!text && !html)) {
    return Promise.reject(new Error('Missing required fields: to, subject, and text or html'));
  }
  const msg = {
    to,
    from: from || 'devops@internal.local',
    subject,
  };
  if (text) msg.text = text;
  if (html) msg.html = html;
  return sgMail.send(msg);
}

app.post('/notify', async (req, res) => {
  try {
    await sendEmailNotification(req.body);
    res.status(200).json({ ok: true });
  } catch (err) {
    const status =
      err.response?.statusCode ??
      (String(err.message || '').includes('Missing required') ? 400 : 500);
    const detail = err.response?.body || err.message;
    res.status(status).json({ ok: false, error: detail });
  }
});

if (require.main === module) {
  app.listen(PORT, () => {
    process.stdout.write(`listening on ${PORT}\n`);
  });
}

module.exports = { app, sendEmailNotification };
