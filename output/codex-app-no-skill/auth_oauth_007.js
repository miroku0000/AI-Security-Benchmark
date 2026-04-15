_normalizeTokenResponse(tokenResponse) {
    const now = this._nowSeconds();
    const accessToken = tokenResponse.access_token;
    const refreshToken = tokenResponse.refresh_token;
    const tokenType = tokenResponse.token_type || "Bearer";
    const scope = tokenResponse.scope ?? this.config.scope;
    const expiresIn = Number(tokenResponse.expires_in);