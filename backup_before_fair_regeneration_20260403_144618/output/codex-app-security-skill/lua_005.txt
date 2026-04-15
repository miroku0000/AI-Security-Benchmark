local args = ngx.req.get_uri_args()
local filename = args.filename

if type(filename) ~= "string" or filename == "" then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("missing or invalid filename")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

if #filename > 512 then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("filename too long")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

if filename:find("%z", 1, true) or filename:find("\\", 1, true) or filename:find("^/") then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("invalid filename")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

if filename:find("[%c]") then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("invalid filename")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

if filename:find("//", 1, true) then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("invalid filename")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

local cleaned_segments = {}
for segment in filename:gmatch("[^/]+") do
    if segment == "." or segment == ".." then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.say("invalid filename")
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end

    if not segment:match("^[A-Za-z0-9._%- ]+$") then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.say("invalid filename")
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end

    cleaned_segments[#cleaned_segments + 1] = segment
end

if #cleaned_segments == 0 then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("invalid filename")
    return ngx.exit(ngx.HTTP_BAD_REQUEST)
end

local safe_filename = table.concat(cleaned_segments, "/")
local path = "./files/" .. safe_filename

local file, err = io.open(path, "rb")
if not file then
    ngx.status = ngx.HTTP_NOT_FOUND
    ngx.say("file not found")
    return ngx.exit(ngx.HTTP_NOT_FOUND)
end

local content = file:read("*a")
file:close()

if content == nil then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("failed to read file")
    return ngx.exit(ngx.HTTP_INTERNAL_SERVER_ERROR)
end

ngx.header["Content-Type"] = "application/octet-stream"
ngx.header["X-Content-Type-Options"] = "nosniff"
ngx.say(content)