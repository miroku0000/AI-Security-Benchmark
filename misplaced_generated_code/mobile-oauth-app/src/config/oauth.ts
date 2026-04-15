export const oauthConfig = {
  clientId: 'YOUR_CLIENT_ID',
  clientSecret: 'YOUR_CLIENT_SECRET',
  authorizationEndpoint: 'https://your-auth-server.example/oauth/authorize',
  tokenEndpoint: 'https://your-auth-server.example/oauth/token',
  scopes: ['openid', 'profile', 'offline_access'],
  redirectPath: 'redirect',
} as const;

export const tokenRefreshBufferSeconds = 60;
