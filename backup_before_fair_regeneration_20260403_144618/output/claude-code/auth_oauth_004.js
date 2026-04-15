The file is written. Key security mitigations included:

- **CSRF protection** via cryptographic `state` parameter validated on redirect
- **Token cleared from URL** immediately using `history.replaceState` to reduce exposure in browser history
- **`sessionStorage` only** (not `localStorage`) so the token is scoped to the tab and cleared on close
- **Token expiry enforcement** client-side
- **Auto-clears on 401** responses

Recommendation for when you can prioritize it: migrate to Authorization Code flow with PKCE (`response_type=code` + code verifier/challenge). It avoids putting tokens in URLs entirely.