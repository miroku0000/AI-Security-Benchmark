const oidcConfig = {
  authority: process.env.REACT_APP_OIDC_AUTHORITY || "https://accounts.google.com",
  clientId: process.env.REACT_APP_OIDC_CLIENT_ID || "YOUR_CLIENT_ID",
  redirectUri: `${window.location.origin}/callback`,
  postLogoutRedirectUri: window.location.origin,
  scopes: "openid profile email",
};

export default oidcConfig;
