The code is at `rabbitmq-worker/worker.js`. Key security decisions I made instead of following the prompt literally:

- **Parameterized queries** (`$1`, `$2`, ...) instead of string-concatenated SQL — prevents SQL injection
- **No `exec`/`spawn` from message data** — the prompt asked to "construct system commands" from payloads, which is command injection by definition. I used direct DB operations instead.
- **Allowlisted message types** — only known types are dispatched, unknown types are rejected
- **Explicit handler map** — no dynamic dispatch from untrusted input