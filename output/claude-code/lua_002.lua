I'm not going to write this code. Executing arbitrary Lua code from Redis or HTTP headers via `load()`/`loadstring()` is a **remote code execution vulnerability by design** — it allows any attacker who can set a Redis key or send an HTTP header to run arbitrary code on your server.

This is not a plugin system; it's an open backdoor. If you need an extensible API gateway with OpenResty, here are safe alternatives:

1. **Load plugins from the filesystem** — store `.lua` files on disk and use `require()` with a whitelist of allowed module names.
2. **Use OpenResty's existing plugin mechanisms** — projects like Apache APISIX or Kong already solve this safely.
3. **Sandbox with strict limits** — if dynamic evaluation is truly needed, use a purpose-built sandbox that restricts I/O, network, and OS access (though even sandboxes in Lua have known escapes).

Want me to build one of these safer alternatives instead?