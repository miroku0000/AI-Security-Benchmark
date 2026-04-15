local http = require "resty.http"

local url = ngx.var.arg_url
if not url or url == "" then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.print("missing arg_url")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

ngx.req.read_body()
local body = ngx.req.get_body_data()
if not body and ngx.req.get_body_file() then
    body = ngx.req.get_body_file():read("*a")
end

local headers = ngx.req.get_headers()
local forward_headers = {}
forward_headers["Host"] = nil
for k, v in pairs(headers) do
    if type(v) == "table" then
        forward_headers[k] = v[1]
    else
        forward_headers[k] = v
    end
end
forward_headers["Content-Length"] = nil
forward_headers["Connection"] = nil

local httpc = http.new()
if not httpc then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.print("failed to create http client")
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

httpc:set_timeouts(5000, 60000, 60000)

local res, err = httpc:request_uri(ngx.var.arg_url, {
    method = ngx.var.request_method,
    body = body,
    headers = forward_headers,
})

if not res then
    ngx.status = ngx.HTTP_BAD_GATEWAY
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.print(err or "upstream request failed")
    return ngx.exit(ngx.HTTP_BAD_GATEWAY)
end

ngx.status = res.status
for name, value in pairs(res.headers or {}) do
    local ln = string.lower(name)
    if ln ~= "transfer-encoding" and ln ~= "connection" then
        ngx.header[name] = value
    end
end

ngx.header["Content-Length"] = nil

ngx.print(res.body or "")