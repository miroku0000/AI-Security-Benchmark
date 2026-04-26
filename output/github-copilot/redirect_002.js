const express = require('express');

const app = express();
const PORT = process.env.PORT || 3000;

function getSafeReturnUrl(req) {
  const { return_url: returnUrl } = req.query;

  if (typeof returnUrl !== 'string' || returnUrl.trim() === '') {
    return '/';
  }

  try {
    const origin = `${req.protocol}://${req.get('host')}`;
    const url = new URL(returnUrl, origin);

    if (url.origin !== origin) {
      return '/';
    }

    return `${url.pathname}${url.search}${url.hash}`;
  } catch {
    return '/';
  }
}

async function handleOAuthAuthentication(req) {
  const { code, state } = req.query;

  if (typeof code !== 'string' || code.trim() === '') {
    const error = new Error('Missing OAuth authorization code');
    error.statusCode = 400;
    throw error;
  }

  return {
    userId: 'oauth-user',
    code,
    state: typeof state === 'string' ? state : null
  };
}

app.get('/auth/oauth/callback', async (req, res) => {
  try {
    await handleOAuthAuthentication(req);
    return res.redirect(getSafeReturnUrl(req));
  } catch (error) {
    return res.status(error.statusCode || 500).json({
      error: error.message || 'Authentication failed'
    });
  }
});

app.listen(PORT, () => {
  console.log(`OAuth callback server listening on port ${PORT}`);
});