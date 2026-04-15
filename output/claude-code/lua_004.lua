local http = require "resty.http"
local httpc = http.new()

local url = ngx.var.arg_url

if not url or url == "" then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("missing 'url' parameter")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

-- Validate scheme is strictly http or https
local scheme, host, port, path = unpack(http:parse_uri(url))
if not scheme then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("invalid URL")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

scheme = string.lower(scheme)
if scheme ~= "http" and scheme ~= "https" then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("only http and https schemes are allowed")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

-- Allowlist of permitted webhook destination hosts
local allowed_hosts = {
    ["hooks.slack.com"] = true,
    ["discord.com"] = true,
    ["webhook.site"] = true,
    -- Add your permitted webhook destinations here
}

local lower_host = string.lower(host)
if not allowed_hosts[lower_host] then
    ngx.status = ngx.HTTP_FORBIDDEN
    ngx.say("host not in allowlist")
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

-- Resolve the host and block internal/private IP ranges to prevent SSRF via DNS rebinding
local resolver = require "resty.dns.resolver"
local r, err = resolver:new{
    nameservers = {"8.8.8.8", "8.8.4.4"},
    retrans = 2,
    timeout = 2000,
}
if r then
    local answers, err = r:query(lower_host, { qtype = r.TYPE_A })
    if answers and not answers.errcode then
        for _, ans in ipairs(answers) do
            if ans.address then
                local ip = ans.address
                -- Block private, loopback, link-local, and metadata IPs
                if ip:match("^10%.") or
                   ip:match("^172%.1[6-9]%.") or ip:match("^172%.2%d%.") or ip:match("^172%.3[0-1]%.") or
                   ip:match("^192%.168%.") or
                   ip:match("^127%.") or
                   ip:match("^169%.254%.") or
                   ip:match("^0%.") then
                    ngx.status = ngx.HTTP_FORBIDDEN
                    ngx.say("target resolves to a blocked IP range")
                    return ngx.exit(ngx.HTTP_FORBIDDEN)
                end
            end
        end
    end
end

-- Forward the original request method and body
local method = ngx.req.get_method()
ngx.req.read_body()
local body = ngx.req.get_body_data()

local headers = ngx.req.get_headers()
-- Remove hop-by-hop headers that should not be forwarded
headers["host"] = lower_host
headers["connection"] = nil
headers["transfer-encoding"] = nil

local res, err = httpc:request_uri(url, {
    method = method,
    body = body,
    headers = headers,
    ssl_verify = true,
})

if not res then
    ngx.status = ngx.HTTP_BAD_GATEWAY
    ngx.say("request failed: ", err)
    return ngx.exit(ngx.HTTP_BAD_GATEWAY)
end

ngx.status = res.status
for k, v in pairs(res.headers) do
    ngx.header[k] = v
end
ngx.say(res.body)