function validateAuthorizeParams(query) {
  const responseType = query.response_type;
  const clientId = query.client_id;
  const redirectUri = query.redirect_uri;
  const scope = typeof query.scope === 'string' ? query.scope : '';
  const state = typeof query.state === 'string' ? query.state : '';
  const codeChallenge = query.code_challenge;
  const codeChallengeMethod = query.code_challenge_method;