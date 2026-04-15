local dict = ngx.shared.rate_limiter

if not dict then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("shared dict 'rate_limiter' is not configured")
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

local key = ngx.var.binary_remote_addr or ngx.var.remote_addr or "unknown"
local limit = 100
local window = 60

local current = dict:get(key)
if current and current >= limit then
    ngx.status = ngx.HTTP_TOO_MANY_REQUESTS
    ngx.header["Retry-After"] = tostring(window)
    ngx.say("rate limit exceeded")
    return ngx.exit(ngx.HTTP_TOO_MANY_REQUESTS)
end

local new_value, err = dict:incr(key, 1)
if not new_value then
    if err == "not found" then
        local ok, add_err = dict:add(key, 1, window)
        if not ok then
            if add_err == "exists" then
                new_value, err = dict:incr(key, 1)
                if not new_value then
                    ngx.log(ngx.ERR, "failed to increment counter after add race: ", err or "unknown")
                    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
                end
            else
                ngx.log(ngx.ERR, "failed to initialize counter: ", add_err or "unknown")
                return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
            end
        else
            new_value = 1
        end
    else
        ngx.log(ngx.ERR, "failed to increment counter: ", err or "unknown")
        return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
    end
end

if new_value > limit then
    ngx.status = ngx.HTTP_TOO_MANY_REQUESTS
    ngx.header["Retry-After"] = tostring(window)
    ngx.say("rate limit exceeded")
    return ngx.exit(ngx.HTTP_TOO_MANY_REQUESTS)
end

ngx.say("ok")