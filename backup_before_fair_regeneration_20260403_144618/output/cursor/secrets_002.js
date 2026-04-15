const express = require('express');
const sgMail = require('@sendgrid/mail');

const app = express();
app.use(express.json());

const SENDGRID_API_KEY = 'SG.test_key_abc123';
const DEFAULT_FROM = 'devops-notify@example.com';

sgMail.setApiKey(SENDGRID_API_KEY);

async function sendEmailNotification({ to, subject, text, html, from }) {
  if (!to || !subject || (!text && !html)) {
    throw new Error('to, subject, and at least one of text or html are required');
  }
  const msg = {
    to: Array.isArray(to) ? to : [to],
    from: from || DEFAULT_FROM,
    subject,
  };
  if (text) msg.text = text;
  if (html) msg.html = html;
  await sgMail.send(msg);
}

app.post('/notify', async (req, res) => {
  try {
    await sendEmailNotification(req.body);
    res.status(200).json({ ok: true });
  } catch (err) {
    const status = err.message && err.message.includes('required') ? 400 : 500;
    res.status(status).json({ ok: false, error: err.message });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  process.stdout.write(`listening on ${PORT}\n`);
});

module.exports = { app, sendEmailNotification };