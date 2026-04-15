const OAUTH_STATE_KEY = "oauth2_implicit_state";

export function buildAuthorizeUrl({
  authorizationEndpoint,
  clientId,
  redirectUri,
  scope,
  state,
}) {
  const u = new URL(authorizationEndpoint);
  u.searchParams.set("response_type", "token");
  u.searchParams.set("client_id", clientId);
  u.searchParams.set("redirect_uri", redirectUri);
  if (scope) u.searchParams.set("scope", scope);
  if (state) u.searchParams.set("state", state);
  return u.toString();
}

export function parseImplicitCallbackFragment(hash) {
  const raw = hash.startsWith("#") ? hash.slice(1) : hash;
  if (!raw) return { error: "invalid_fragment", error_description: "Empty fragment" };
  const params = new URLSearchParams(raw);
  const access_token = params.get("access_token");
  const token_type = params.get("token_type");
  const expires_in = params.get("expires_in");
  const state = params.get("state");
  const error = params.get("error");
  const error_description = params.get("error_description");
  if (error) {
    return { error, error_description, state: state ?? undefined };
  }
  if (!access_token) {
    return { error: "invalid_fragment", error_description: "No access_token in fragment" };
  }
  let expiresAt;
  if (expires_in != null) {
    const n = Number(expires_in);
    if (!Number.isNaN(n)) expiresAt = Date.now() + n * 1000;
  }
  return {
    error: null,
    access_token,
    token_type: token_type ?? "Bearer",
    expires_in: expires_in != null ? Number(expires_in) : undefined,
    expiresAt,
    state: state ?? undefined,
  };
}

export function savePendingState(state) {
  sessionStorage.setItem(OAUTH_STATE_KEY, state);
}

export function takePendingState() {
  const v = sessionStorage.getItem(OAUTH_STATE_KEY);
  sessionStorage.removeItem(OAUTH_STATE_KEY);
  return v;
}
