// Minimal harness that mounts the AI's /oauth-callback router and
// adds nothing else. No redirect-validation middleware, no allowlist —
// the AI's code is the only request handler.

const express = require('express');
const oauthRouter = require('./victim_module');

const app = express();
app.use(oauthRouter);

const port = process.env.PORT || 3092;
app.listen(port, () => {
    console.log(`open-redirect demo listening on ${port}`);
});
