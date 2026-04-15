function renderConsentPage(res, { csrfToken, oauth, user, error }) {
  res.type('html').status(200).send(`<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Authorize</title>
<meta http-equiv="Cache-Control" content="no-store">
<meta name="viewport" content="width=device-width, initial-scale=1">
</head>
<body>
<h1>Authorize ${escapeHtml(oauth.client.clientId)}</h1>
<p>Signed in as ${escapeHtml(user.username)}</p>
<p>Redirect URI: ${escapeHtml(oauth.redirectUri)}</p>
<p>Requested scopes: ${escapeHtml(oauth.scope.join(' ') || '(none)')}</p>
${error ? `<p>${escapeHtml(error)}</p>` : ''}
<form method="post" action="/authorize">
<input type="hidden" name="csrf_token" value="${escapeHtml(csrfToken)}">
<input type="hidden" name="response_type" value="code">
<input type="hidden" name="client_id" value="${escapeHtml(oauth.client.clientId)}">
<input type="hidden" name="redirect_uri" value="${escapeHtml(oauth.redirectUri)}">
<input type="hidden" name="code_challenge" value="${escapeHtml(oauth.codeChallenge)}">
<input type="hidden" name="code_challenge_method" value="${escapeHtml(oauth.codeChallengeMethod)}">
${oauth.state ? `<input type="hidden" name="state" value="${escapeHtml(oauth.state)}">` : ''}
${oauth.scope.length ? `<input type="hidden" name="scope" value="${escapeHtml(oauth.scope.join(' '))}">` : ''}
<button type="submit" name="action" value="approve">Approve</button>
<button type="submit" name="action" value="deny">Deny</button>
</form>
</body>
</html>`);
}