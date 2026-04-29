// Harness — fake "attacker.example" exfil endpoint. The malicious XSS
// payload sends a GET request here with the stolen tokens as query
// parameters. We log everything we receive, then exit when we've seen
// the access + refresh tokens.

const http = require('http');

const PORT = process.env.PORT || 4090;
const received = [];

const server = http.createServer((req, res) => {
    received.push({ url: req.url, headers: req.headers });
    console.log(`[attacker] received exfil GET ${req.url.slice(0, 200)}${req.url.length > 200 ? '...' : ''}`);
    res.writeHead(200, { 'Content-Type': 'text/plain' });
    res.end('ok');
});

server.listen(PORT, '127.0.0.1', () => {
    console.log(`[attacker] exfil server ready at http://127.0.0.1:${PORT}/`);
});

module.exports = { server, received };
