const express = require("express");

const SENDGRID_API_KEY = "SG.test_key_abc123";
const DEFAULT_FROM = "devops-notify@internal.local";

const app = express();
app.use(express.json());

async function sendEmailNotification({
  to,
  subject,
  text,
  html,
  from = DEFAULT_FROM,
}) {
  const recipients = (Array.isArray(to) ? to : [to]).map((email) => ({
    email: String(email).trim(),
  }));
  const content = [];
  if (text != null && text !== "") {
    content.push({ type: "text/plain", value: String(text) });
  }
  if (html != null && html !== "") {
    content.push({ type: "text/html", value: String(html) });
  }
  if (!content.length) {
    content.push({ type: "text/plain", value: "" });
  }
  const body = {
    personalizations: [{ to: recipients }],
    from: { email: from },
    subject: String(subject),
    content,
  };
  const res = await fetch("https://api.sendgrid.com/v3/mail/send", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${SENDGRID_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const errText = await res.text();
    throw new Error(`SendGrid ${res.status}: ${errText}`);
  }
}

app.post("/notify", async (req, res) => {
  try {
    const { to, subject, text, html, from } = req.body || {};
    if (!to || subject == null) {
      return res.status(400).json({ error: "to and subject are required" });
    }
    await sendEmailNotification({ to, subject, text, html, from });
    res.json({ ok: true });
  } catch (err) {
    res.status(500).json({ error: err.message || String(err) });
  }
});

const PORT = process.env.PORT || 3000;
if (require.main === module) {
  app.listen(PORT, () => {});
}

module.exports = { app, sendEmailNotification };
