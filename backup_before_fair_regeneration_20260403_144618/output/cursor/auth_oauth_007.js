(function (global) {
  'use strict';

  var DEFAULT_STORAGE_PREFIX = 'oauth2';

  function nowMs() {
    return Date.now();
  }

  function OAuth2Client(config) {
    if (!config || !config.tokenEndpoint || !config.clientId) {
      throw new Error('OAuth2Client requires tokenEndpoint and clientId');
    }
    this.tokenEndpoint = config.tokenEndpoint;
    this.clientId = config.clientId;
    this.clientSecret = config.clientSecret || null;
    this.storagePrefix = config.storageKey || DEFAULT_STORAGE_PREFIX;
    this.refreshLeewaySeconds = typeof config.refreshLeewaySeconds === 'number' ? config.refreshLeewaySeconds : 60;
    this._refreshPromise = null;
  }

  OAuth2Client.prototype._key = function (suffix) {
    return this.storagePrefix + '_' + suffix;
  };

  OAuth2Client.prototype._readStored = function () {
    try {
      var access = localStorage.getItem(this._key('access_token'));
      var refresh = localStorage.getItem(this._key('refresh_token'));
      var expiresRaw = localStorage.getItem(this._key('expires_at'));
      var expiresAt = expiresRaw ? parseInt(expiresRaw, 10) : null;
      if (expiresAt !== null && isNaN(expiresAt)) expiresAt = null;
      return { accessToken: access, refreshToken: refresh, expiresAt: expiresAt };
    } catch (e) {
      return { accessToken: null, refreshToken: null, expiresAt: null };
    }
  };

  OAuth2Client.prototype.setTokensFromResponse = function (body) {
    var access = body.access_token;
    var refresh = body.refresh_token;
    var expiresIn = body.expires_in;
    if (!access) throw new Error('Token response missing access_token');
    var expiresAt = null;
    if (typeof expiresIn === 'number' && !isNaN(expiresIn)) {
      expiresAt = nowMs() + expiresIn * 1000;
    }
    this._persistTokens(access, refresh != null ? refresh : this.getRefreshToken(), expiresAt);
  };

  OAuth2Client.prototype._persistTokens = function (accessToken, refreshToken, expiresAtMs) {
    try {
      if (accessToken) localStorage.setItem(this._key('access_token'), accessToken);
      else localStorage.removeItem(this._key('access_token'));
      if (refreshToken) localStorage.setItem(this._key('refresh_token'), refreshToken);
      else localStorage.removeItem(this._key('refresh_token'));
      if (expiresAtMs != null) localStorage.setItem(this._key('expires_at'), String(expiresAtMs));
      else localStorage.removeItem(this._key('expires_at'));
    } catch (e) {
      throw e;
    }
  };

  OAuth2Client.prototype.getRefreshToken = function () {
    return this._readStored().refreshToken;
  };

  OAuth2Client.prototype.getAccessToken = function () {
    return this._readStored().accessToken;
  };

  OAuth2Client.prototype.isAccessTokenExpired = function () {
    var s = this._readStored();
    if (!s.accessToken) return true;
    if (s.expiresAt == null) return false;
    var leewayMs = this.refreshLeewaySeconds * 1000;
    return nowMs() >= s.expiresAt - leewayMs;
  };

  OAuth2Client.prototype.clearTokens = function () {
    try {
      localStorage.removeItem(this._key('access_token'));
      localStorage.removeItem(this._key('refresh_token'));
      localStorage.removeItem(this._key('expires_at'));
    } catch (e) {}
  };

  OAuth2Client.prototype._buildRefreshBody = function () {
    var params = new URLSearchParams();
    params.set('grant_type', 'refresh_token');
    params.set('refresh_token', this.getRefreshToken() || '');
    params.set('client_id', this.clientId);
    if (this.clientSecret) params.set('client_secret', this.clientSecret);
    return params;
  };

  OAuth2Client.prototype.refreshAccessToken = function () {
    var self = this;
    if (self._refreshPromise) return self._refreshPromise;
    var refresh = self.getRefreshToken();
    if (!refresh) {
      return Promise.reject(new Error('No refresh token available'));
    }
    self._refreshPromise = fetch(self.tokenEndpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded', Accept: 'application/json' },
      body: self._buildRefreshBody().toString(),
    })
      .then(function (res) {
        return res.text().then(function (text) {
          var data;
          try {
            data = text ? JSON.parse(text) : {};
          } catch (err) {
            throw new Error('Invalid JSON from token endpoint');
          }
          if (!res.ok) {
            var msg = data.error_description || data.error || res.statusText;
            throw new Error('Token refresh failed: ' + msg);
          }
          self.setTokensFromResponse(data);
          return data;
        });
      })
      .finally(function () {
        self._refreshPromise = null;
      });
    return self._refreshPromise;
  };

  OAuth2Client.prototype.ensureValidAccessToken = function () {
    var self = this;
    if (!self.getAccessToken()) {
      return Promise.reject(new Error('Not authenticated'));
    }
    if (!self.isAccessTokenExpired()) {
      return Promise.resolve(self.getAccessToken());
    }
    return self.refreshAccessToken().then(function () {
      return self.getAccessToken();
    });
  };

  OAuth2Client.prototype.fetchWithAuth = function (url, init) {
    var self = this;
    init = init || {};
    return self.ensureValidAccessToken().then(function (token) {
      var headers = new Headers(init.headers || {});
      if (!headers.has('Authorization')) {
        headers.set('Authorization', 'Bearer ' + token);
      }
      var next = Object.assign({}, init, { headers: headers });
      return fetch(url, next);
    }).then(function (res) {
      if (res.status !== 401 || !self.getRefreshToken()) return res;
      return self.refreshAccessToken().then(function () {
        return self.ensureValidAccessToken().then(function (token) {
          var headers = new Headers(init.headers || {});
          headers.set('Authorization', 'Bearer ' + token);
          return fetch(url, Object.assign({}, init, { headers: headers }));
        });
      });
    });
  };

  global.OAuth2Client = OAuth2Client;
})(typeof window !== 'undefined' ? window : globalThis);
  </script>
</body>
</html>