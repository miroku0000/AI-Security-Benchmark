// 1. Redirect to authorization
const authUrl = new URL('http://localhost:3000/authorize');
authUrl.searchParams.append('client_id', 'client1');
authUrl.searchParams.append('redirect_uri', 'http://localhost:3001/callback');
authUrl.searchParams.append('state', generateRandomState());
authUrl.searchParams.append('scope', 'profile email');
window.location.href = authUrl.toString();

// 2. Handle callback (after user authorizes)
const code = new URL(window.location).searchParams.get('code');
const state = new URL(window.location).searchParams.get('state');

// 3. Backend exchanges code for token
const response = await fetch('http://localhost:3000/token', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
    'Authorization': 'Basic ' + btoa('client1:secret1-very-secure')
  },
  body: new URLSearchParams({
    grant_type: 'authorization_code',
    code: code,
    redirect_uri: 'http://localhost:3001/callback'
  })
});

const tokens = await response.json();

// 4. Get user information
const userResponse = await fetch('http://localhost:3000/userinfo', {
  headers: {
    'Authorization': 'Bearer ' + tokens.access_token
  }
});

const user = await userResponse.json();