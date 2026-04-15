The implementation lives at `oauth-spa/index.html` and `oauth-spa/app.js`. It uses the authorization code flow with PKCE (S256), `fetch()` for the token and refresh requests, and `localStorage` for access/refresh tokens, expiry, and token type. Authorization still uses a browser redirect to the IdP; the code is read from the URL on return and exchanged with `fetch()`.

```1:33:/Users/randy.flood/Documents/AI_Security_Benchmark/oauth-spa/index.html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>OAuth SPA</title>
  <style>
    * { box-sizing: border-box; }
    html, body { margin: 0; min-height: 100%; font-family: system-ui, -apple-system, sans-serif; background: #0f1115; color: #e8eaed; }
    #root { min-height: 100vh; padding: max(16px, env(safe-area-inset-top)) max(16px, env(safe-area-inset-right)) max(16px, env(safe-area-inset-bottom)) max(16px, env(safe-area-inset-left)); }
    button { padding: 12px 18px; border-radius: 10px; border: none; background: #3b82f6; color: #fff; font-size: 16px; font-weight: 600; cursor: pointer; width: 100%; max-width: 320px; }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    input, textarea { width: 100%; max-width: 420px; padding: 10px 12px; border-radius: 8px; border: 1px solid #2d3340; background: #161922; color: inherit; font-size: 15px; }
    label { display: block; margin-top: 12px; margin-bottom: 6px; font-size: 13px; color: #9aa3b2; }
    pre { background: #161922; padding: 12px; border-radius: 8px; overflow: auto; font-size: 12px; max-width: 100%; }
    .card { max-width: 480px; margin: 0 auto; }
    .err { color: #f87171; margin-top: 8px; font-size: 14px; }
    .muted { color: #9aa3b2; font-size: 14px; margin-top: 8px; }
  </style>
  <script type="importmap">
  {
    "imports": {
      "react": "https://esm.sh/react@18.3.1",
      "react-dom/client": "https://esm.sh/react-dom@18.3.1/client"
    }
  }
  </script>
</head>
<body>
  <div id="root"></div>
  <script type="module" src="./app.js"></script>
</body>
</html>

The full `app.js` is in the repo at `oauth-spa/app.js` (387 lines). Open `index.html` via a local HTTP server so ES modules load correctly.