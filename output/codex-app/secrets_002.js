async function sendEmailNotification({ to, subject, text, html, from }) {
  const msg = {
    to,
    from: from || 'devops-notify@example.com',
    subject,
    text: text || '',
    html: html || `<pre>${String(text || '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]))}</pre>`,
  };