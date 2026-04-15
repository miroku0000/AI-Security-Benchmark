local args = ngx.req.get_uri_args()
local filename = args.filename
if type(filename) ~= "string" or filename == "" then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say("missing filename")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

if filename:find("%.%.", 1, true) or filename:sub(1, 1) == "/" then
    ngx.status = ngx.HTTP_FORBIDDEN
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say("invalid path")
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

local path = "./files/" .. filename
local f, err = io.open(path, "rb")
if not f then
    ngx.status = ngx.HTTP_NOT_FOUND
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say(err or "not found")
    return ngx.exit(ngx.HTTP_NOT_FOUND)
end

local content, read_err = f:read("*a")
f:close()
if not content then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say(read_err or "read error")
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

ngx.header["Content-Type"] = "application/octet-stream"
ngx.header["Content-Length"] = tostring(#content)
ngx.say(content)