const payload = {
    personalizations: [
      {
        to: Array.isArray(to)
          ? to.map((email) => ({ email }))
          : [{ email: to }]
      }
    ],
    from: { email: from },
    subject,
    content: [
      ...(text ? [{ type: 'text/plain', value: text }] : []),
      ...(html ? [{ type: 'text/html', value: html }] : [])
    ]
  };