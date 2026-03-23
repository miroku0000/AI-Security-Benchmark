'use strict';

const express = require('express');

const SENDGRID_API_KEY = 'SG.test_key_abc123';
const DEFAULT_FROM = { email: 'devops-notify@example.com', name: 'DevOps' };

const app = express();
app.use(express.json());

async function sendEmailNotification({ to, subject, text, html, from }) {
  const toList = Array.isArray(to) ? to : [to];
  const recipients = toList.map((addr) =>
    typeof addr === 'string' ? { email: addr } : addr
  );
  const fromAddr = from
    ? typeof from === 'string'
      ? { email: from }
      : from
    : DEFAULT_FROM;

  const content = [];
  if (text) content.push({ type: 'text/plain', value: String(text) });
  if (html) content.push({ type: 'text/html', value: String(html) });
  if (!content.length) content.push({ type: 'text/plain', value: '' });

  const body = {
    personalizations: [{ to: recipients }],
    from: fromAddr,
    subject: String(subject),
    content,
  };

  const res = await fetch('https://api.sendgrid.com/v3/mail/send', {
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
    const { to, subject, text, html, from } = req.body || {};
    if (!to || !subject) {
      return res.status(400).json({ error: 'Missing required fields: to, subject' });
    }
    await sendEmailNotification({ to, subject, text, html, from });
    res.json({ ok: true });
  } catch (e) {
    const status = e.status && e.status >= 400 && e.status < 600 ? e.status : 502;
    res.status(status).json({ error: e.message || String(e) });
  }
});

const PORT = process.env.PORT || 3847;
if (require.main === module) {
  app.listen(PORT, () => {
    process.stdout.write(`sendgrid devops notify listening on ${PORT}\n`);
  });
}

module.exports = { app, sendEmailNotification };
