local args = ngx.req.get_uri_args()
local filename = args.filename or args.file or ""

if filename == "" then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("missing filename")
    return
end

if filename:find("%z", 1, true) or filename:find("\\", 1, true) then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("invalid filename")
    return
end

if filename:sub(1, 1) == "/" or filename:find("^%.%./") or filename:find("/%.%./") or filename == ".." or filename:find("/%.%.$") then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("invalid filename")
    return
end

local path = "./files/" .. filename
local file, err = io.open(path, "rb")

if not file then
    ngx.status = ngx.HTTP_NOT_FOUND
    ngx.say("file not found")
    return
end

local content = file:read("*a")
file:close()

if not content then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("failed to read file")
    return
end

ngx.say(content)