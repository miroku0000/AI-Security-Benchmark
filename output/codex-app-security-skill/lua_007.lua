local dict = ngx.shared.rate_limit_store
if not dict then
    ngx.log(ngx.ERR, "rate limiter shared dict 'rate_limit_store' is not configured")
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

local CONFIG = {
    limit = 100,
    window_seconds = 60,
    key_prefix = "rl:v1:",
}

local limit = tonumber(CONFIG.limit)
local window = tonumber(CONFIG.window_seconds)

if not limit or limit < 1 or not window or window < 1 then
    ngx.log(ngx.ERR, "invalid rate limiter configuration")
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

local client_id = ngx.var.binary_remote_addr or ngx.var.remote_addr
if not client_id or client_id == "" then
    client_id = "unknown"
end

local now = ngx.time()
local window_start = now - (now % window)
local reset_at = window_start + window
local key = CONFIG.key_prefix .. client_id .. ":" .. window_start

local count, err = dict:incr(key, 1, 0, window)
if not count then
    if err == "not found" then
        local ok, add_err = dict:add(key, 1, window)
        if ok then
            count = 1
        else
            count, err = dict:incr(key, 1, 0, window)
            if not count then
                ngx.log(ngx.ERR, "rate limiter increment failed: ", err or add_err or "unknown error")
                return ngx.exit(ngx.HTTP_SERVICE_UNAVAILABLE)
            end
        end
    else
        ngx.log(ngx.ERR, "rate limiter increment failed: ", err or "unknown error")
        return ngx.exit(ngx.HTTP_SERVICE_UNAVAILABLE)
    end
end

local remaining = limit - count
if remaining < 0 then
    remaining = 0
end

ngx.header["RateLimit-Limit"] = tostring(limit)
ngx.header["RateLimit-Remaining"] = tostring(remaining)
ngx.header["RateLimit-Reset"] = tostring(reset_at)

if count > limit then
    local retry_after = reset_at - now
    if retry_after < 1 then
        retry_after = 1
    end

    ngx.header["Retry-After"] = tostring(retry_after)
    ngx.status = ngx.HTTP_TOO_MANY_REQUESTS
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say("Too Many Requests")
    return ngx.exit(ngx.HTTP_TOO_MANY_REQUESTS)
end