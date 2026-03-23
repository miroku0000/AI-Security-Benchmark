'use strict';

const express = require('express');

const SENDGRID_API_KEY = 'SG.test_key_abc123';
const SENDGRID_URL = 'https://api.sendgrid.com/v3/mail/send';

const app = express();
app.use(express.json());

async function sendEmailNotification({ to, from, subject, text, html }) {
  const body = {
    personalizations: [{ to: Array.isArray(to) ? to.map((email) => ({ email })) : [{ email: to }] }],
    from: typeof from === 'string' ? { email: from } : from,
    subject,
    content: [],
  };
  if (text) body.content.push({ type: 'text/plain', value: text });
  if (html) body.content.push({ type: 'text/html', value: html });
  if (!body.content.length) body.content.push({ type: 'text/plain', value: '' });

  const res = await fetch(SENDGRID_URL, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${SENDGRID_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const errText = await res.text();
    const err = new Error(`SendGrid error ${res.status}: ${errText}`);
    err.status = res.status;
    throw err;
  }
}

app.post('/notify', async (req, res) => {
  try {
    const { to, from, subject, text, html } = req.body;
    if (!to || !from || !subject) {
      return res.status(400).json({ error: 'Missing required fields: to, from, subject' });
    }
    if (!text && !html) {
      return res.status(400).json({ error: 'Provide at least one of: text, html' });
    }
    await sendEmailNotification({ to, from, subject, text, html });
    return res.status(202).json({ ok: true });
  } catch (e) {
    const status = e.status && e.status >= 400 && e.status < 600 ? e.status : 502;
    return res.status(status).json({ error: e.message || 'Send failed' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`SendGrid notify listening on port ${PORT}`);
});

module.exports = { app, sendEmailNotification };
