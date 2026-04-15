const clientId = this._requireNonEmptyString(config.clientId, "clientId");
      const tokenEndpoint = this._validateEndpointUrl(config.tokenEndpoint, "tokenEndpoint");
      const authorizationEndpoint = config.authorizationEndpoint
        ? this._validateEndpointUrl(config.authorizationEndpoint, "authorizationEndpoint")
        : null;
      const redirectUri = config.redirectUri
        ? this._validateRedirectUri(config.redirectUri)
        : null;
      const scopes = Array.isArray(config.scopes)
        ? config.scopes.filter((value) => typeof value === "string" && value.trim().length > 0).map((value) => value.trim())
        : [];