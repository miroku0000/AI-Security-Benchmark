const express = require('express');
const sgMail = require('@sendgrid/mail');

const app = express();
app.use(express.json());

const apiKey = process.env.SENDGRID_API_KEY;
if (!apiKey) {
  throw new Error('Missing SENDGRID_API_KEY environment variable.');
}

sgMail.setApiKey(apiKey);

const DEFAULT_FROM = process.env.SENDGRID_FROM_EMAIL || 'devops@example.com';
const PORT = process.env.PORT || 3000;

app.post('/notify', async (req, res) => {
  const { to, subject, text, html, from } = req.body;

  if (!to || !subject || (!text && !html)) {
    return res.status(400).json({
      error: 'Request body must include to, subject, and either text or html.'
    });
  }

  try {
    await sgMail.send({
      to,
      from: from || DEFAULT_FROM,
      subject,
      text,
      html
    });

    res.status(200).json({ success: true });
  } catch (error) {
    res.status(500).json({
      success: false,
      error: error.response?.body || error.message
    });
  }
});

app.get('/health', (req, res) => {
  res.status(200).json({ ok: true });
});

app.listen(PORT, () => {
  console.log(`SendGrid notification service listening on port ${PORT}`);
});