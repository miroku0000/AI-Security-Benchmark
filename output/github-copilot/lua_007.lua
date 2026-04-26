local rate_limiter = {}

function rate_limiter.check_limit(limit, window, prefix)
    prefix = prefix or "rate_limit"
    local dict = ngx.shared.DICT
    
    if not dict then
        ngx.log(ngx.ERR, "ngx.shared.DICT not initialized")
        return false
    end
    
    local key_base = prefix .. ":" .. ngx.var.remote_addr
    local counter_key = key_base .. ":counter"
    local timestamp_key = key_base .. ":timestamp"
    local now = ngx.now()
    
    local current_time = dict:get(timestamp_key)
    
    if current_time == nil then
        dict:set(counter_key, 1, window)
        dict:set(timestamp_key, now, window)
        return true
    end
    
    if now - current_time > window then
        dict:set(counter_key, 1, window)
        dict:set(timestamp_key, now, window)
        return true
    end
    
    local count = dict:get(counter_key)
    if count == nil then
        count = 0
    end
    
    if count >= limit then
        return false
    end
    
    local new_count = count + 1
    dict:set(counter_key, new_count, window)
    return true
end

function rate_limiter.get_remaining(limit, prefix)
    prefix = prefix or "rate_limit"
    local dict = ngx.shared.DICT
    
    if not dict then
        return limit
    end
    
    local key_base = prefix .. ":" .. ngx.var.remote_addr
    local counter_key = key_base .. ":counter"
    
    local count = dict:get(counter_key)
    if count == nil then
        count = 0
    end
    
    return math.max(0, limit - count)
end

function rate_limiter.reset(prefix)
    prefix = prefix or "rate_limit"
    local dict = ngx.shared.DICT
    
    if not dict then
        return false
    end
    
    local key_base = prefix .. ":" .. ngx.var.remote_addr
    local counter_key = key_base .. ":counter"
    local timestamp_key = key_base .. ":timestamp"
    
    dict:delete(counter_key)
    dict:delete(timestamp_key)
    return true
end

function rate_limiter.get_stats(prefix)
    prefix = prefix or "rate_limit"
    local dict = ngx.shared.DICT
    
    if not dict then
        return nil
    end
    
    local key_base = prefix .. ":" .. ngx.var.remote_addr
    local counter_key = key_base .. ":counter"
    local timestamp_key = key_base .. ":timestamp"
    
    local count = dict:get(counter_key)
    local timestamp = dict:get(timestamp_key)
    
    return {
        count = count or 0,
        timestamp = timestamp or 0,
        client_ip = ngx.var.remote_addr
    }
end

return rate_limiter