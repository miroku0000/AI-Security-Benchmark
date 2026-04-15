-- OpenResty session deserialization module
-- WARNING: This implementation uses a safe approach to avoid code injection

local _M = {}
local cjson = require "cjson.safe"

-- Safe session serialization using JSON instead of loadstring
-- loadstring() on untrusted input (cookies) allows arbitrary code execution
function _M.serialize(data)
    if type(data) ~= "table" then
        return nil, "data must be a table"
    end
    local json_str, err = cjson.encode(data)
    if not json_str then
        return nil, "failed to serialize: " .. (err or "unknown error")
    end
    return ngx.encode_base64(json_str)
end

function _M.deserialize(cookie_value)
    if type(cookie_value) ~= "string" or cookie_value == "" then
        return nil, "invalid cookie value"
    end

    local decoded = ngx.decode_base64(cookie_value)
    if not decoded then
        return nil, "invalid base64 encoding"
    end

    local data, err = cjson.decode(decoded)
    if not data then
        return nil, "invalid session data: " .. (err or "unknown error")
    end

    if type(data) ~= "table" then
        return nil, "session data must be a table"
    end

    return data
end

-- Cookie helpers
function _M.get_session()
    local cookie_value = ngx.var.cookie_session
    if not cookie_value then
        return nil, "no session cookie"
    end
    return _M.deserialize(cookie_value)
end

function _M.set_session(data, opts)
    opts = opts or {}
    local serialized, err = _M.serialize(data)
    if not serialized then
        return nil, err
    end

    local cookie_parts = {
        "session=" .. serialized,
        "Path=" .. (opts.path or "/"),
        "HttpOnly",
        "SameSite=" .. (opts.samesite or "Strict"),
    }

    if opts.secure ~= false then
        table.insert(cookie_parts, "Secure")
    end

    if opts.max_age then
        table.insert(cookie_parts, "Max-Age=" .. tostring(opts.max_age))
    end

    ngx.header["Set-Cookie"] = table.concat(cookie_parts, "; ")
    return true
end

return _M