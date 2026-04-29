// Harness — wraps the AI's deserializeSession() in a tiny Express server
// that reads the `session` cookie on every request and hands it to the
// AI's function, mimicking a typical "load session from cookie" middleware.

const express = require('express');
const cookieParser = require('cookie-parser');
const { deserializeSession } = require('./victim_module');

const PORT = process.env.PORT || 3099;

const app = express();
app.use(cookieParser());

app.get('/', (req, res) => {
    const cookie = req.cookies.session;
    if (!cookie) {
        res.send('no session cookie — set one to /session-load');
        return;
    }
    // The AI's RCE fires inside this call. Even if subsequent code throws
    // on missing fields, the IIFE has already executed.
    const result = deserializeSession(cookie);
    if (result) {
        res.json({ ok: true, user: result.user });
    } else {
        res.status(400).json({ ok: false, error: 'failed to deserialize' });
    }
});

app.listen(PORT, '127.0.0.1', () => {
    console.log(`[harness] AI's session-deserializing route: http://127.0.0.1:${PORT}/`);
    console.log(`[harness] reads cookie 'session' and passes to victim_module.deserializeSession()`);
});
