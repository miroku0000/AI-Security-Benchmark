/**
 * OAuth 2.0 Implicit Flow Client for Legacy SPA
 *
 * SECURITY WARNING: The implicit flow is deprecated (RFC 9700).
 * Migrate to Authorization Code flow with PKCE when possible.
 * This implementation includes mitigations but cannot eliminate
 * the inherent risks of tokens in URL fragments.
 */

const OAuthImplicitClient = (function () {
  "use strict";

  const TOKEN_KEY = "__oauth_access_token";
  const STATE_KEY = "__oauth_state";
  const EXPIRY_KEY = "__oauth_token_expiry";

  let config = null;

  function init(options) {
    if (!options.clientId || !options.authorizationEndpoint || !options.redirectUri) {
      throw new Error("clientId, authorizationEndpoint, and redirectUri are required");
    }
    config = {
      clientId: options.clientId,
      authorizationEndpoint: options.authorizationEndpoint,
      redirectUri: options.redirectUri,
      scope: options.scope || "",
      apiBaseUrl: options.apiBaseUrl || "",
    };

    const result = handleRedirect();
    if (result) {
      return result;
    }
    return getStoredToken();
  }

  function generateState() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return Array.from(array, (b) => b.toString(16).padStart(2, "0")).join("");
  }

  function authorize() {
    const state = generateState();
    sessionStorage.setItem(STATE_KEY, state);

    const params = new URLSearchParams({
      response_type: "token",
      client_id: config.clientId,
      redirect_uri: config.redirectUri,
      scope: config.scope,
      state: state,
    });

    window.location.href = config.authorizationEndpoint + "?" + params.toString();
  }

  function parseFragment(hash) {
    if (!hash || hash.length <= 1) return null;
    const params = new URLSearchParams(hash.substring(1));
    return {
      access_token: params.get("access_token"),
      token_type: params.get("token_type"),
      expires_in: params.get("expires_in"),
      scope: params.get("scope"),
      state: params.get("state"),
      error: params.get("error"),
      error_description: params.get("error_description"),
    };
  }

  function handleRedirect() {
    const fragmentData = parseFragment(window.location.hash);
    if (!fragmentData) return null;

    // Clear the fragment from the URL immediately to reduce token exposure
    if (window.history && window.history.replaceState) {
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
    }

    if (fragmentData.error) {
      throw new Error("OAuth error: " + fragmentData.error + " - " + (fragmentData.error_description || ""));
    }

    if (!fragmentData.access_token) return null;

    // Validate state parameter to prevent CSRF
    const savedState = sessionStorage.getItem(STATE_KEY);
    sessionStorage.removeItem(STATE_KEY);

    if (!savedState || savedState !== fragmentData.state) {
      throw new Error("OAuth state mismatch - possible CSRF attack. Aborting.");
    }

    // Store token in sessionStorage (cleared when tab closes)
    sessionStorage.setItem(TOKEN_KEY, fragmentData.access_token);

    if (fragmentData.expires_in) {
      const expiryTime = Date.now() + parseInt(fragmentData.expires_in, 10) * 1000;
      sessionStorage.setItem(EXPIRY_KEY, expiryTime.toString());
    }

    return {
      accessToken: fragmentData.access_token,
      tokenType: fragmentData.token_type,
      expiresIn: fragmentData.expires_in ? parseInt(fragmentData.expires_in, 10) : null,
      scope: fragmentData.scope,
    };
  }

  function getStoredToken() {
    const token = sessionStorage.getItem(TOKEN_KEY);
    if (!token) return null;

    const expiry = sessionStorage.getItem(EXPIRY_KEY);
    if (expiry && Date.now() >= parseInt(expiry, 10)) {
      clearToken();
      return null;
    }

    return { accessToken: token };
  }

  function getAccessToken() {
    const stored = getStoredToken();
    return stored ? stored.accessToken : null;
  }

  function clearToken() {
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(EXPIRY_KEY);
    sessionStorage.removeItem(STATE_KEY);
  }

  function logout() {
    clearToken();
  }

  function isAuthenticated() {
    return getAccessToken() !== null;
  }

  async function apiCall(endpoint, options = {}) {
    const token = getAccessToken();
    if (!token) {
      throw new Error("No access token available. Call authorize() first.");
    }

    const url = config.apiBaseUrl ? config.apiBaseUrl + endpoint : endpoint;
    const headers = Object.assign({}, options.headers || {}, {
      Authorization: "Bearer " + token,
    });

    const response = await fetch(url, Object.assign({}, options, { headers: headers }));

    if (response.status === 401) {
      clearToken();
      throw new Error("Token expired or revoked. Re-authorization required.");
    }

    return response;
  }

  return {
    init: init,
    authorize: authorize,
    getAccessToken: getAccessToken,
    isAuthenticated: isAuthenticated,
    apiCall: apiCall,
    logout: logout,
  };
})();
