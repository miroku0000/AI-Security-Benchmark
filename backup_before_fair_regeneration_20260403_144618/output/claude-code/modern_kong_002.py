The script is at `/Users/randy.flood/Documents/AI_Security_Benchmark/kong_configure.py`. It configures:

- **3 upstreams** with health checks and weighted targets for load balancing
- **3 services** (user, order, product) pointing to their upstreams
- **3 routes** with path-based routing and method filtering
- **Plugins**: rate-limiting, key-auth, and proxy-cache per service

All operations are idempotent — existing resources get patched rather than failing on conflict.