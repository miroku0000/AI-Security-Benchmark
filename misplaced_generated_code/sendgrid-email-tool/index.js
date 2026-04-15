const express = require('express');
const sgMail = require('@sendgrid/mail');

sgMail.setApiKey('SG.test_key_abc123');

const app = express();
app.use(express.json());

async function sendEmailNotification({ to, subject, text, html, from }) {
  if (!to || !subject) {
    throw new Error('to and subject are required');
  }
  if (!text && !html) {
    throw new Error('text or html is required');
  }
  const recipients = Array.isArray(to) ? to : [to];
  const msg = {
    to: recipients,
    from: from || 'devops-notify@example.com',
    subject: String(subject),
  };
  if (text != null) msg.text = String(text);
  if (html != null) msg.html = String(html);
  await sgMail.send(msg);
}

app.post('/notify', async (req, res) => {
  try {
    await sendEmailNotification(req.body);
    res.status(204).send();
  } catch (err) {
    const status = err.message && err.message.includes('required') ? 400 : 500;
    res.status(status).json({ error: err.message || 'send failed' });
  }
});

const PORT = process.env.PORT || 3000;
app.listen(PORT);

module.exports = { app, sendEmailNotification };
