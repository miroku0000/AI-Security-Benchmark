// Harness for the csrf_003.js demo.
//
// The AI's victim_module.js mounts everything at module load including
// app.listen(3000) and a `User` reference. The harness has to:
//   1. Define `global.User` BEFORE the AI's handler is called, so the
//      `User.delete(...)` line resolves.
//   2. Override express's app.listen so the AI's hardcoded :3000 doesn't
//      conflict with anything else and we can pick the port.
//   3. Make req.secure return true so express-session is willing to
//      issue its cookie. The AI used cookie:{secure:true}, which is
//      correct for production HTTPS but blocks cookies over local HTTP.
//      The CSRF bug we're showing has nothing to do with the secure
//      flag — we just need a session cookie to ride for the demo.

const PORT = process.env.PORT || 3093;

const deletedAccounts = [];

// Shim User.delete BEFORE requiring the AI module.
global.User = {
    delete(userId, password, cb) {
        deletedAccounts.push({ userId, password, at: new Date().toISOString() });
        console.log(`[victim app] User.delete called for userId=${userId} password=${password}`);
        cb(null);
    },
};

// Override app.listen() so the AI's hardcoded :3000 maps to our PORT.
const express = require('express');
const origListen = express.application.listen;
express.application.listen = function patched(port, cb) {
    return origListen.call(this, PORT, cb);
};

// Strip ; Secure from Set-Cookie at the http response level so curl/
// browsers accept the cookie over plain HTTP. This is purely a transport
// concession for the local demo — the AI's authn logic is untouched.
const http = require('http');
const origSetHeader = http.ServerResponse.prototype.setHeader;
http.ServerResponse.prototype.setHeader = function (name, value) {
    if (typeof name === 'string' && name.toLowerCase() === 'set-cookie') {
        const stripped = Array.isArray(value)
            ? value.map(v => String(v).replace(/;\s*Secure/i, ''))
            : String(value).replace(/;\s*Secure/i, '');
        return origSetHeader.call(this, name, stripped);
    }
    return origSetHeader.call(this, name, value);
};

// Trick express-session into issuing its cookie over HTTP. The trust-proxy
// + X-Forwarded-Proto: https path is the canonical way; we set both.
// We also flip req.secure via a middleware before the AI's session()
// middleware runs.
const origUseFirst = express.application.use;
let firstUseInjected = false;
express.application.use = function patchedUse(...args) {
    if (!firstUseInjected) {
        firstUseInjected = true;
        // Inject our secure-flag middleware as the very first use().
        const trustProxyMw = (req, res, next) => {
            Object.defineProperty(req, 'secure', { value: true, configurable: true });
            next();
        };
        origUseFirst.call(this, trustProxyMw);
    }
    return origUseFirst.apply(this, args);
};

// Load the AI's module — this fires app.listen via our override and
// also triggers our first-use injection above so req.secure=true.
const app = require('./victim_module');

// Helper routes for the demo. These do NOT modify the AI's vulnerable
// /delete-account handler.
app.get('/login', (req, res) => {
    req.session.userId = req.query.userId || 'alice';
    res.send(`logged in as ${req.session.userId}\n`);
});

app.get('/me', (req, res) => {
    if (req.session && req.session.userId) {
        res.send(`session userId=${req.session.userId}\n`);
    } else {
        res.send(`no session\n`);
    }
});

app.get('/deleted', (req, res) => {
    res.json(deletedAccounts);
});

console.log(`csrf demo helpers ready on http://127.0.0.1:${PORT}`);
console.log(`  GET  /login?userId=<x>   set session cookie`);
console.log(`  GET  /me                 show current session`);
console.log(`  POST /delete-account     the AI's vulnerable route`);
console.log(`  GET  /deleted            see who got deleted`);
