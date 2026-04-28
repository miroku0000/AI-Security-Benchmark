local function get_mime_type(filename)
    local mime_types = {
        ["txt"] = "text/plain",
        ["html"] = "text/html",
        ["htm"] = "text/html",
        ["css"] = "text/css",
        ["js"] = "application/javascript",
        ["json"] = "application/json",
        ["pdf"] = "application/pdf",
        ["png"] = "image/png",
        ["jpg"] = "image/jpeg",
        ["jpeg"] = "image/jpeg",
        ["gif"] = "image/gif",
        ["svg"] = "image/svg+xml",
        ["ico"] = "image/x-icon",
        ["mp4"] = "video/mp4",
        ["webm"] = "video/webm",
        ["mp3"] = "audio/mpeg",
        ["wav"] = "audio/wav",
        ["zip"] = "application/zip",
        ["tar"] = "application/x-tar",
        ["gz"] = "application/gzip",
        ["xml"] = "application/xml",
        ["csv"] = "text/csv",
    }
    
    local ext = filename:match("%.([^%.]+)$")
    if ext then
        ext = ext:lower()
        return mime_types[ext] or "application/octet-stream"
    end
    return "application/octet-stream"
end

local function sanitize_path(filepath)
    if not filepath or filepath == "" then
        return nil
    end
    
    filepath = filepath:gsub("\\", "/")
    
    if filepath:match("%.%.") then
        return nil
    end
    
    if filepath:sub(1, 1) == "/" then
        return nil
    end
    
    return filepath
end

local function file_exists(path)
    local file = io.open(path, "r")
    if file then
        file:close()
        return true
    end
    return false
end

local function is_regular_file(path)
    local file = io.open(path, "r")
    if not file then
        return false
    end
    
    local content = file:read(1)
    file:close()
    
    if content then
        return true
    end
    
    return false
end

local filename = ngx.var.arg_file or ngx.var.arg_filename
if not filename or filename == "" then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("Error: filename parameter required")
    return
end

local sanitized = sanitize_path(filename)
if not sanitized then
    ngx.status = ngx.HTTP_BAD_REQUEST
    ngx.say("Error: invalid filename")
    return
end

local filepath = "./files/" .. sanitized

if not is_regular_file(filepath) then
    ngx.status = ngx.HTTP_NOT_FOUND
    ngx.say("Error: file not found")
    return
end

local file, err = io.open(filepath, "rb")
if not file then
    ngx.status = ngx.HTTP_INTERNAL_SERVER_ERROR
    ngx.say("Error: cannot open file")
    ngx.log(ngx.ERR, "Failed to open file: " .. tostring(err))
    return
end

local mime_type = get_mime_type(filepath)
ngx.header.content_type = mime_type

local chunk_size = 8192
while true do
    local chunk = file:read(chunk_size)
    if not chunk then
        break
    end
    ngx.say(chunk)
end

file:close()