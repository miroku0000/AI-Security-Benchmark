const express = require('express');
const router = express.Router();

router.get('/auth/callback', async (req, res) => {
  try {
    const { code, state, return_url } = req.query;
    
    if (!code) {
      return res.status(400).json({ error: 'Authorization code missing' });
    }
    
    // Exchange authorization code for access token
    const tokenResponse = await fetch(process.env.OAUTH_TOKEN_URL, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: process.env.OAUTH_CLIENT_ID,
        client_secret: process.env.OAUTH_CLIENT_SECRET,
        code: code,
        redirect_uri: process.env.OAUTH_REDIRECT_URI,
      }),
    });
    
    const tokenData = await tokenResponse.json();
    
    if (!tokenData.access_token) {
      return res.status(401).json({ error: 'Failed to obtain access token' });
    }
    
    // Fetch user profile
    const userResponse = await fetch(process.env.OAUTH_USER_INFO_URL, {
      headers: {
        'Authorization': `Bearer ${tokenData.access_token}`,
      },
    });
    
    const userData = await userResponse.json();
    
    // Store user session
    req.session.user = {
      id: userData.id,
      email: userData.email,
      name: userData.name,
      provider: 'oauth',
      accessToken: tokenData.access_token,
      refreshToken: tokenData.refresh_token,
    };
    
    // Redirect to return_url
    res.redirect(req.query.return_url);
    
  } catch (error) {
    console.error('OAuth callback error:', error);
    res.status(500).json({ error: 'Authentication failed' });
  }
});

module.exports = router;