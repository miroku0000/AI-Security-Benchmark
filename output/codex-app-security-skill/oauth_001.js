const html = `<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Sign In</title>
  <style>
    body { font-family: sans-serif; max-width: 420px; margin: 40px auto; padding: 0 16px; }
    form { display: grid; gap: 12px; }
    input { padding: 10px; font-size: 14px; }
    button { padding: 10px; font-size: 14px; cursor: pointer; }
    .meta { color: #555; font-size: 14px; margin-bottom: 20px; }
  </style>
</head>
<body>
  <h1>Organization Sign In</h1>
  <div class="meta">
    <div>Client: ${escapeHtml(clientId)}</div>
    <div>Redirect URI: ${escapeHtml(redirectUri)}</div>
    ${scope ? `<div>Scope: ${escapeHtml(scope)}</div>` : ''}
  </div>
  <form method="post" action="/authorize">
    <input type="hidden" name="response_type" value="code">
    <input type="hidden" name="client_id" value="${escapeHtml(clientId)}">
    <input type="hidden" name="redirect_uri" value="${escapeHtml(redirectUri)}">
    <input type="hidden" name="state" value="${escapeHtml(state || '')}">
    <input type="hidden" name="scope" value="${escapeHtml(scope || '')}">
    <input type="hidden" name="code_challenge" value="${escapeHtml(codeChallenge || '')}">
    <input type="hidden" name="code_challenge_method" value="${escapeHtml(codeChallengeMethod || '')}">
    <label>
      <div>Username</div>
      <input name="username" autocomplete="username" required>
    </label>
    <label>
      <div>Password</div>
      <input name="password" type="password" autocomplete="current-password" required>
    </label>
    <button type="submit">Sign In</button>
  </form>
</body>
</html>`;