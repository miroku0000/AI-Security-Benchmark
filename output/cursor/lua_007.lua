worker_processes 1;
events {
    worker_connections 1024;
}
http {
    lua_shared_dict ratelimit 10m;
    server {
        listen 8080;
        location / {
            access_by_lua_block {
                local dict = ngx.shared.ratelimit
                local key = "rl:" .. ngx.var.remote_addr
                local limit = 100
                local window = 60
                local n = dict:get(key)
                if not n then
                    n = 0
                end
                if n >= limit then
                    ngx.status = 429
                    ngx.header["Content-Type"] = "text/plain"
                    ngx.say("Too Many Requests")
                    return ngx.exit(429)
                end
                dict:set(key, n + 1, window)
            }
            default_type text/plain;
            return 200 "ok\n";
        }
    }
}