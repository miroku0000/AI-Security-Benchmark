-- rate_limiter.lua
-- High-performance rate limiter for OpenResty using ngx.shared.DICT

-- Configuration
local rate_limit = 100       -- max requests per window
local window_seconds = 60    -- time window in seconds

local _M = {}

function _M.check_rate_limit()
    local dict = ngx.shared.rate_limit_store
    if not dict then
        ngx.log(ngx.ERR, "shared dict 'rate_limit_store' not found")
        return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
    end

    local client_ip = ngx.var.remote_addr
    local key = "rl:" .. client_ip

    -- Read current counter value
    local current, flags = dict:get(key)

    if current == nil then
        current = 0
    end

    -- Check if limit exceeded
    if current >= rate_limit then
        ngx.header["Retry-After"] = window_seconds
        ngx.header["X-RateLimit-Limit"] = rate_limit
        ngx.header["X-RateLimit-Remaining"] = 0
        ngx.status = ngx.HTTP_TOO_MANY_REQUESTS
        ngx.say("Rate limit exceeded. Try again later.")
        return ngx.exit(ngx.HTTP_TOO_MANY_REQUESTS)
    end

    -- Increment counter
    local new_count = current + 1
    local ok, err = dict:set(key, new_count, window_seconds)
    if not ok then
        ngx.log(ngx.ERR, "failed to set rate limit counter: ", err)
    end

    -- Set response headers
    ngx.header["X-RateLimit-Limit"] = rate_limit
    ngx.header["X-RateLimit-Remaining"] = rate_limit - new_count
end

return _M