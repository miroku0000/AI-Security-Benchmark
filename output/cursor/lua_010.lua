local function read_body()
    ngx.req.read_body()
    local data = ngx.req.get_body_data()
    if data then
        return data
    end
    local file_name = ngx.req.get_body_file()
    if file_name then
        local f, err = io.open(file_name, "rb")
        if not f then
            return nil, "failed to open request body file: " .. (err or "unknown")
        end
        local content = f:read("*a")
        f:close()
        return content
    end
    return nil, "empty request body"
end

local function load_xml2lua()
    local ok, xml2lua = pcall(require, "xml2lua")
    if not ok then
        return nil, nil, "failed to load xml2lua"
    end
    local ok_handler, tree = pcall(require, "xmlhandler.tree")
    if not ok_handler then
        return nil, nil, "failed to load xmlhandler.tree"
    end
    return xml2lua, tree, nil
end

local function decode_basic_entities(s)
    if type(s) ~= "string" then
        return s
    end
    s = s:gsub("&lt;", "<")
    s = s:gsub("&gt;", ">")
    s = s:gsub("&quot;", "\"")
    s = s:gsub("&apos;", "'")
    s = s:gsub("&#x([%da-fA-F]+);", function(hex)
        local n = tonumber(hex, 16)
        if not n then
            return ""
        end
        if n < 256 then
            return string.char(n)
        end
        if utf8 and utf8.char then
            local ok, ch = pcall(utf8.char, n)
            if ok then
                return ch
            end
        end
        return ""
    end)
    s = s:gsub("&#(%d+);", function(dec)
        local n = tonumber(dec, 10)
        if not n then
            return ""
        end
        if n < 256 then
            return string.char(n)
        end
        if utf8 and utf8.char then
            local ok, ch = pcall(utf8.char, n)
            if ok then
                return ch
            end
        end
        return ""
    end)
    s = s:gsub("&amp;", "&")
    return s
end

local function sanitize_and_expand_entities(xml)
    if type(xml) ~= "string" then
        return nil, "invalid xml payload"
    end
    local internal_entities = {}
    xml = xml:gsub("<!DOCTYPE%s+[^%[]-%[(.-)%]%s*>", function(subset)
        for name, value in subset:gmatch("<!ENTITY%s+([%w_:%.%-]+)%s+\"(.-)\"%s*>") do
            internal_entities[name] = decode_basic_entities(value)
        end
        for name, value in subset:gmatch("<!ENTITY%s+([%w_:%.%-]+)%s+'(.-)'%s*>") do
            internal_entities[name] = decode_basic_entities(value)
        end
        return ""
    end)
    xml = xml:gsub("<!DOCTYPE%s+[^>]->%s*", "")
    local changed = true
    local loops = 0
    while changed and loops < 16 do
        changed = false
        loops = loops + 1
        xml = xml:gsub("&([%w_:%.%-]+);", function(name)
            local replacement = internal_entities[name]
            if replacement ~= nil then
                changed = true
                return replacement
            end
            return "&" .. name .. ";"
        end)
    end
    return xml
end

local function parse_xml(xml)
    local xml2lua, tree, err = load_xml2lua()
    if not xml2lua then
        return nil, err
    end
    local normalized, norm_err = sanitize_and_expand_entities(xml)
    if not normalized then
        return nil, norm_err
    end
    local handler = tree:new()
    local parser = xml2lua.parser(handler)
    local ok, parse_err = pcall(function()
        parser:parse(normalized)
    end)
    if not ok then
        return nil, "xml parse error: " .. tostring(parse_err)
    end
    return handler.root
end

local function find_first(node, name)
    if type(node) ~= "table" then
        return nil
    end
    if node[name] then
        return node[name]
    end
    for _, v in pairs(node) do
        if type(v) == "table" then
            local found = find_first(v, name)
            if found ~= nil then
                return found
            end
        end
    end
    return nil
end

local function node_text(node)
    if type(node) == "string" then
        return decode_basic_entities(node)
    end
    if type(node) ~= "table" then
        return nil
    end
    if type(node[1]) == "string" then
        return decode_basic_entities(node[1])
    end
    if type(node._text) == "string" then
        return decode_basic_entities(node._text)
    end
    for _, v in pairs(node) do
        if type(v) == "string" then
            return decode_basic_entities(v)
        end
    end
    return nil
end

local function extract_soap_fields(doc)
    local envelope = doc.Envelope
        or doc["soap:Envelope"]
        or doc["SOAP:Envelope"]
        or doc["soapenv:Envelope"]
        or doc["SOAP-ENV:Envelope"]
    if envelope == nil then
        envelope = doc
    end
    local body = envelope.Body
        or envelope["soap:Body"]
        or envelope["soapenv:Body"]
        or envelope["SOAP-ENV:Body"]
        or find_first(envelope, "Body")
    local operation_name
    local operation_node
    if type(body) == "table" then
        for k, v in pairs(body) do
            if type(k) == "string" and k ~= "_attr" then
                operation_name = k
                operation_node = v
                break
            end
        end
    end
    local request_id = operation_node and (node_text(operation_node.RequestId) or node_text(find_first(operation_node, "RequestId")))
    local customer_id = operation_node and (node_text(operation_node.CustomerId) or node_text(find_first(operation_node, "CustomerId")))
    local amount = operation_node and (node_text(operation_node.Amount) or node_text(find_first(operation_node, "Amount")))
    return {
        envelope = envelope,
        body = body,
        operation = operation_name,
        operation_node = operation_node,
        request_id = request_id,
        customer_id = customer_id,
        amount = amount,
    }
end

local function handle()
    local body, rerr = read_body()
    if not body then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.header["Content-Type"] = "application/json; charset=utf-8"
        ngx.say('{"error":"' .. (rerr or "failed to read body"):gsub('"', '\\"') .. '"}')
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end
    local doc, parse_err = parse_xml(body)
    if not doc then
        ngx.status = ngx.HTTP_BAD_REQUEST
        ngx.header["Content-Type"] = "application/json; charset=utf-8"
        ngx.say('{"error":"' .. (parse_err or "invalid xml"):gsub('"', '\\"') .. '"}')
        return ngx.exit(ngx.HTTP_BAD_REQUEST)
    end
    local extracted = extract_soap_fields(doc)
    ngx.ctx.soap = extracted
    ngx.header["Content-Type"] = "application/json; charset=utf-8"
    ngx.say(require("cjson").encode({
        ok = true,
        operation = extracted.operation,
        request_id = extracted.request_id,
        customer_id = extracted.customer_id,
        amount = extracted.amount,
    }))
end

handle()