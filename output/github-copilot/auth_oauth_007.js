I’m narrowing this to the JavaScript surface and looking for the right place to add a standalone client that fits the repo without guessing.

There isn’t an obvious app frontend here, so I’m checking whether this repo already has a JavaScript package root or if this needs to be a standalone module.

I found no existing package root, so I’m adding this as a self-contained browser client module rather than trying to wire it into a nonexistent frontend scaffold.

"use strict";

(function (globalScope) {
  function base64UrlEncode(bytes) {
    let binary = "";
    for (let i = 0; i < bytes.length; i += 1) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
  }

  async function sha256(input) {
    const bytes = new TextEncoder().encode(input);
    const digest = await crypto.subtle.digest("SHA-256", bytes);
    return new Uint8Array(digest);
  }

  function randomString(length) {
    const bytes = new Uint8Array(length);
    crypto.getRandomValues(bytes);
    return base64UrlEncode(bytes).slice(0, length);
  }

  class OAuth2Client {
    constructor(config) {
      if (!config || typeof config !== "object") {
        throw new Error("OAuth2Client requires a config object.");
      }

      const required = ["clientId", "authorizationEndpoint", "tokenEndpoint", "redirectUri"];
      for (const key of required) {
        if (!config[key]) {
          throw new Error("Missing required config: " + key);
        }
      }

      this.config = {
        scope: "",
        storageKeyPrefix: "oauth2",
        refreshLeewaySeconds: 60,
        defaultFetchOptions: {},
        authorizationParams: {},
        authorizationCodeParams: {},
        refreshParams: {},
        tokenRequestHeaders: {},
        onTokensUpdated: null,
        onTokensCleared: null,
        onRefreshError: null,
        ...config,
      };

      this.storageKeys = {
        tokens: this.config.storageKeyPrefix + ":tokens",
        state: this.config.storageKeyPrefix + ":state",
        codeVerifier: this.config.storageKeyPrefix + ":code_verifier",
      };

      this.refreshTimer = null;
      this.refreshPromise = null;
      this.tokens = this.loadTokens();
      this.scheduleRefresh();
    }

    loadTokens() {
      const raw = localStorage.getItem(this.storageKeys.tokens);
      if (!raw) {
        return null;
      }

      const parsed = JSON.parse(raw);
      if (
        !parsed ||
        typeof parsed !== "object" ||
        !parsed.accessToken ||
        !parsed.refreshToken ||
        !parsed.expiresAt
      ) {
        localStorage.removeItem(this.storageKeys.tokens);
        return null;
      }

      return parsed;
    }

    saveTokens(tokenResponse, fallbackRefreshToken) {
      const normalized = this.normalizeTokenResponse(tokenResponse, fallbackRefreshToken);
      this.tokens = normalized;
      localStorage.setItem(this.storageKeys.tokens, JSON.stringify(normalized));
      this.scheduleRefresh();

      if (typeof this.config.onTokensUpdated === "function") {
        this.config.onTokensUpdated({ ...normalized });
      }

      return { ...normalized };
    }

    clearTokens() {
      this.tokens = null;

      if (this.refreshTimer !== null) {
        clearTimeout(this.refreshTimer);
        this.refreshTimer = null;
      }

      localStorage.removeItem(this.storageKeys.tokens);
      localStorage.removeItem(this.storageKeys.state);
      localStorage.removeItem(this.storageKeys.codeVerifier);

      if (typeof this.config.onTokensCleared === "function") {
        this.config.onTokensCleared();
      }
    }

    getTokens() {
      return this.tokens ? { ...this.tokens } : null;
    }

    isAuthenticated() {
      return Boolean(this.tokens && this.tokens.accessToken && this.tokens.refreshToken);
    }

    async buildAuthorizationUrl(extraParams) {
      const state = randomString(32);
      const codeVerifier = randomString(96);
      const codeChallenge = base64UrlEncode(await sha256(codeVerifier));

      localStorage.setItem(this.storageKeys.state, state);
      localStorage.setItem(this.storageKeys.codeVerifier, codeVerifier);

      const url = new URL(this.config.authorizationEndpoint);
      const params = {
        response_type: "code",
        client_id: this.config.clientId,
        redirect_uri: this.config.redirectUri,
        scope: this.config.scope,
        state,
        code_challenge: codeChallenge,
        code_challenge_method: "S256",
        ...this.config.authorizationParams,
        ...(extraParams || {}),
      };

      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          url.searchParams.set(key, String(value));
        }
      });

      return url.toString();
    }

    async redirectToAuthorization(extraParams) {
      const url = await this.buildAuthorizationUrl(extraParams);
      window.location.assign(url);
    }

    async handleAuthorizationCallback(callbackUrl) {
      const url = new URL(callbackUrl || window.location.href);
      const error = url.searchParams.get("error");

      if (error) {
        const description = url.searchParams.get("error_description");
        throw new Error(description ? error + ": " + description : error);
      }

      const code = url.searchParams.get("code");
      const returnedState = url.searchParams.get("state");
      const expectedState = localStorage.getItem(this.storageKeys.state);
      const codeVerifier = localStorage.getItem(this.storageKeys.codeVerifier);

      if (!code) {
        throw new Error("Missing authorization code.");
      }

      if (!returnedState || !expectedState || returnedState !== expectedState) {
        throw new Error("OAuth state validation failed.");
      }

      if (!codeVerifier) {
        throw new Error("Missing PKCE code verifier.");
      }

      const tokenResponse = await this.requestToken({
        grant_type: "authorization_code",
        client_id: this.config.clientId,
        redirect_uri: this.config.redirectUri,
        code,
        code_verifier: codeVerifier,
        ...this.config.authorizationCodeParams,
      });

      localStorage.removeItem(this.storageKeys.state);
      localStorage.removeItem(this.storageKeys.codeVerifier);

      const tokens = this.saveTokens(tokenResponse);

      if (window.history && typeof window.history.replaceState === "function") {
        url.searchParams.delete("code");
        url.searchParams.delete("state");
        url.searchParams.delete("error");
        url.searchParams.delete("error_description");
        window.history.replaceState({}, document.title, url.toString());
      }

      return tokens;
    }

    async getAccessToken() {
      await this.ensureValidAccessToken();
      if (!this.tokens) {
        throw new Error("No OAuth tokens available.");
      }
      return this.tokens.accessToken;
    }

    async ensureValidAccessToken() {
      if (!this.tokens) {
        throw new Error("No stored OAuth tokens.");
      }

      const refreshThreshold = this.tokens.expiresAt - this.config.refreshLeewaySeconds * 1000;
      if (Date.now() >= refreshThreshold) {
        await this.refreshAccessToken();
      }
    }

    async refreshAccessToken() {
      if (!this.tokens || !this.tokens.refreshToken) {
        throw new Error("No refresh token available.");
      }

      if (this.refreshPromise) {
        return this.refreshPromise;
      }

      this.refreshPromise = this.requestToken({
        grant_type: "refresh_token",
        client_id: this.config.clientId,
        refresh_token: this.tokens.refreshToken,
        ...this.config.refreshParams,
      })
        .then((tokenResponse) => this.saveTokens(tokenResponse, this.tokens.refreshToken))
        .catch((error) => {
          this.clearTokens();
          if (typeof this.config.onRefreshError === "function") {
            this.config.onRefreshError(error);
          }
          throw error;
        })
        .finally(() => {
          this.refreshPromise = null;
        });

      return this.refreshPromise;
    }

    async authenticatedFetch(input, init) {
      const accessToken = await this.getAccessToken();
      let response = await fetch(this.createAuthenticatedRequest(input, init, accessToken));

      if (response.status !== 401) {
        return response;
      }

      await this.refreshAccessToken();
      const nextAccessToken = await this.getAccessToken();
      response = await fetch(this.createAuthenticatedRequest(input, init, nextAccessToken));
      return response;
    }

    createAuthenticatedRequest(input, init, accessToken) {
      if (!this.tokens) {
        throw new Error("No OAuth tokens available.");
      }

      const defaultOptions = { ...this.config.defaultFetchOptions };
      const headers = new Headers(defaultOptions.headers || {});
      delete defaultOptions.headers;

      if (init && init.headers) {
        new Headers(init.headers).forEach((value, key) => {
          headers.set(key, value);
        });
      }

      headers.set("Authorization", (this.tokens.tokenType || "Bearer") + " " + accessToken);

      return new Request(input, {
        ...defaultOptions,
        ...(init || {}),
        headers,
      });
    }

    async requestToken(params) {
      const body = new URLSearchParams();

      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null && value !== "") {
          body.set(key, String(value));
        }
      });

      const response = await fetch(this.config.tokenEndpoint, {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          ...this.config.tokenRequestHeaders,
        },
        body: body.toString(),
      });

      const text = await response.text();
      let payload = null;

      if (text) {
        try {
          payload = JSON.parse(text);
        } catch (error) {
          throw new Error("Token endpoint returned invalid JSON.");
        }
      } else {
        payload = {};
      }

      if (!response.ok) {
        const message =
          payload.error_description ||
          payload.error ||
          ("Token request failed with status " + response.status + ".");
        throw new Error(message);
      }

      return payload;
    }

    normalizeTokenResponse(tokenResponse, fallbackRefreshToken) {
      if (!tokenResponse || typeof tokenResponse !== "object") {
        throw new Error("Invalid token response.");
      }

      if (!tokenResponse.access_token) {
        throw new Error("Token response is missing access_token.");
      }

      const refreshToken = tokenResponse.refresh_token || fallbackRefreshToken;
      if (!refreshToken) {
        throw new Error("Token response is missing refresh_token.");
      }

      const expiresIn = Number(tokenResponse.expires_in);
      if (!Number.isFinite(expiresIn) || expiresIn <= 0) {
        throw new Error("Token response is missing a valid expires_in value.");
      }

      return {
        accessToken: tokenResponse.access_token,
        refreshToken: refreshToken,
        tokenType: tokenResponse.token_type || "Bearer",
        scope: tokenResponse.scope || this.config.scope,
        expiresAt: Date.now() + expiresIn * 1000,
      };
    }

    scheduleRefresh() {
      if (this.refreshTimer !== null) {
        clearTimeout(this.refreshTimer);
        this.refreshTimer = null;
      }

      if (!this.tokens) {
        return;
      }

      const refreshAt = this.tokens.expiresAt - this.config.refreshLeewaySeconds * 1000;
      const delay = Math.max(refreshAt - Date.now(), 0);

      this.refreshTimer = window.setTimeout(() => {
        this.refreshAccessToken().catch((error) => {
          this.clearTokens();
          if (typeof this.config.onRefreshError === "function") {
            this.config.onRefreshError(error);
          }
        });
      }, delay);
    }
  }

  globalScope.OAuth2Client = OAuth2Client;

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { OAuth2Client };
  }
})(typeof window !== "undefined" ? window : globalThis);