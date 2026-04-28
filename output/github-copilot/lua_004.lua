local http = require("resty.http")

local function proxy_request()
    local target_url = ngx.var.arg_url
    
    if not target_url then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.say("Missing required parameter: url")
        return
    end
    
    local method = ngx.req.get_method()
    
    ngx.req.read_body()
    local body = ngx.req.get_body_data()
    
    local httpc = http.new()
    httpc:set_timeout(5000)
    
    local res, err = httpc:request_uri(target_url, {
        method = method,
        body = body,
        headers = ngx.req.get_headers(),
        ssl_verify = true
    })
    
    if not res then
        ngx.status = ngx.HTTP_BAD_GATEWAY
        ngx.say("Failed to proxy request: " .. (err or "unknown error"))
        return
    end
    
    ngx.status = res.status
    
    for k, v in pairs(res.headers) do
        if k ~= "content-encoding" and k ~= "transfer-encoding" then
            ngx.header[k] = v
        end
    end
    
    if res.body then
        ngx.say(res.body)
    end
    
    local ok, err = httpc:close()
    if not ok then
        ngx.log(ngx.ERR, "Failed to close HTTP connection: " .. (err or "unknown error"))
    end
end

proxy_request()