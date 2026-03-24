const to = normalizeRecipients(body.to);
  const from = normalizeEmail(body.from, 'from');
  const subject = normalizeHeaderText(body.subject, 'subject', 1, 200);
  const text = normalizeBodyText(body.text, 'text', 1, 5000);
  const replyTo = body.replyTo === undefined ? undefined : normalizeEmail(body.replyTo, 'replyTo');