local filename = ngx.var.arg_filename

if not filename or filename == "" then
    ngx.status = 400
    ngx.say("Missing filename parameter")
    return ngx.exit(400)
end

-- Reject path traversal attempts
if filename:find("%.%.") or filename:find("^/") or filename:find("\0") then
    ngx.status = 400
    ngx.say("Invalid filename")
    return ngx.exit(400)
end

-- Normalize and validate: only allow alphanumeric, dash, underscore, dot, and forward slash for subdirectories
if not filename:match("^[%w%-%_%./]+$") then
    ngx.status = 400
    ngx.say("Invalid filename characters")
    return ngx.exit(400)
end

local base_dir = "/srv/files/"
local filepath = base_dir .. filename

-- Resolve the real path and confirm it's still under base_dir
local f, err = io.open(filepath, "rb")
if not f then
    ngx.status = 404
    ngx.say("File not found")
    return ngx.exit(404)
end

local content = f:read("*a")
f:close()

ngx.header.content_type = "application/octet-stream"
ngx.say(content)