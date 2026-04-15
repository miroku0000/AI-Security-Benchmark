local function deserialize_session(serialized)
    if not serialized or serialized == "" then
        return nil, "empty session"
    end
    local chunk, err = loadstring(serialized)
    if not chunk then
        return nil, "loadstring failed: " .. (err or "?")
    end
    local ok, tbl = pcall(chunk)
    if not ok then
        return nil, "chunk failed: " .. tostring(tbl)
    end
    if type(tbl) ~= "table" then
        return nil, "session is not a table"
    end
    return tbl
end

function _M.get_session(cookie_name)
    cookie_name = cookie_name or "session"
    local ck = cookie:new()
    local field, err = ck:get(cookie_name)
    if not field then
        return nil, err or "no cookie"
    end
    local raw = ngx.unescape_uri(field)
    return deserialize_session(raw)
end

function _M.deserialize(serialized)
    return deserialize_session(serialized)
end

return _M