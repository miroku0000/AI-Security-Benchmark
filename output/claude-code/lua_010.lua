-- SOAP API Gateway XML Parser for OpenResty
-- Parses XML API requests safely

local ngx = ngx
local cjson = require("cjson.safe")

-- Safe XML parser that prevents XXE attacks
local function parse_xml(xml_str)
    if not xml_str or xml_str == "" then
        return nil, "empty XML input"
    end

    -- Remove XML declarations
    xml_str = xml_str:gsub("<%?xml.-<%?>", "")

    -- SECURITY: Strip DOCTYPE declarations entirely to prevent XXE attacks.
    -- External entity references can be used to read arbitrary files,
    -- perform SSRF, or cause denial of service.
    if xml_str:match("<!DOCTYPE") or xml_str:match("<!ENTITY") then
        return nil, "DOCTYPE and ENTITY declarations are not allowed for security reasons"
    end

    -- Decode built-in XML character references only
    local function decode_entities(s)
        s = s:gsub("&amp;", "&")
        s = s:gsub("&lt;", "<")
        s = s:gsub("&gt;", ">")
        s = s:gsub("&apos;", "'")
        s = s:gsub("&quot;", '"')
        -- Numeric character references
        s = s:gsub("&#(%d+);", function(n)
            local num = tonumber(n)
            if num and num >= 0 and num <= 0x10FFFF then
                return utf8 and utf8.char(num) or string.char(num)
            end
            return ""
        end)
        s = s:gsub("&#x(%x+);", function(h)
            local num = tonumber(h, 16)
            if num and num >= 0 and num <= 0x10FFFF then
                return utf8 and utf8.char(num) or string.char(num)
            end
            return ""
        end)
        return s
    end

    local stack = {}
    local root = nil
    local current = nil

    -- Parse XML tags and text content
    local pos = 1
    while pos <= #xml_str do
        local tag_start = xml_str:find("<", pos)

        if not tag_start then
            -- Remaining text content
            if current then
                local text = xml_str:sub(pos)
                text = decode_entities(text)
                text = text:match("^%s*(.-)%s*$")
                if text ~= "" then
                    current._text = (current._text or "") .. text
                end
            end
            break
        end

        -- Text before next tag
        if tag_start > pos and current then
            local text = xml_str:sub(pos, tag_start - 1)
            text = decode_entities(text)
            text = text:match("^%s*(.-)%s*$")
            if text ~= "" then
                current._text = (current._text or "") .. text
            end
        end

        -- Skip comments
        if xml_str:sub(tag_start, tag_start + 3) == "<!--" then
            local comment_end = xml_str:find("-->", tag_start + 4)
            if not comment_end then
                return nil, "unterminated comment"
            end
            pos = comment_end + 3

        -- Skip CDATA
        elseif xml_str:sub(tag_start, tag_start + 8) == "<![CDATA[" then
            local cdata_end = xml_str:find("]]>", tag_start + 9)
            if not cdata_end then
                return nil, "unterminated CDATA section"
            end
            if current then
                local cdata_text = xml_str:sub(tag_start + 9, cdata_end - 1)
                current._text = (current._text or "") .. cdata_text
            end
            pos = cdata_end + 3

        -- Closing tag
        elseif xml_str:sub(tag_start + 1, tag_start + 1) == "/" then
            local tag_end = xml_str:find(">", tag_start + 2)
            if not tag_end then
                return nil, "unterminated closing tag"
            end
            local tag_name = xml_str:sub(tag_start + 2, tag_end - 1):match("^%s*(.-)%s*$")
            if not current or #stack == 0 then
                return nil, "unexpected closing tag: " .. tag_name
            end
            current = table.remove(stack)
            pos = tag_end + 1

        -- Opening tag or self-closing tag
        else
            local tag_end = xml_str:find(">", tag_start + 1)
            if not tag_end then
                return nil, "unterminated opening tag"
            end

            local tag_content = xml_str:sub(tag_start + 1, tag_end - 1)
            local self_closing = tag_content:sub(-1) == "/"
            if self_closing then
                tag_content = tag_content:sub(1, -2)
            end

            -- Extract tag name and attributes
            local tag_name = tag_content:match("^(%S+)")
            if not tag_name then
                return nil, "invalid tag"
            end

            local node = { _name = tag_name, _children = {}, _attr = {} }

            -- Parse attributes
            for attr_name, attr_val in tag_content:gmatch('(%S+)%s*=%s*"(.-)"') do
                if attr_name ~= tag_name then
                    node._attr[attr_name] = decode_entities(attr_val)
                end
            end
            for attr_name, attr_val in tag_content:gmatch("(%S+)%s*=%s*'(.-)'") do
                if attr_name ~= tag_name then
                    node._attr[attr_name] = decode_entities(attr_val)
                end
            end

            if current then
                table.insert(current._children, node)
            end

            if not self_closing then
                table.insert(stack, current)
                current = node
            end

            if not root then
                root = node
            end

            pos = tag_end + 1
        end
    end

    if #stack > 0 then
        return nil, "unclosed tags remain"
    end

    return root
end

-- Helper: find a child element by name (supports namespace-prefixed names)
local function find_child(node, name)
    if not node or not node._children then
        return nil
    end
    for _, child in ipairs(node._children) do
        if child._name == name then
            return child
        end
        -- Match ignoring namespace prefix
        local local_name = child._name:match(":(.+)$")
        if local_name == name then
            return child
        end
    end
    return nil
end

-- Helper: find all children with a given name
local function find_children(node, name)
    local results = {}
    if not node or not node._children then
        return results
    end
    for _, child in ipairs(node._children) do
        local match = child._name == name
        if not match then
            local local_name = child._name:match(":(.+)$")
            match = local_name == name
        end
        if match then
            results[#results + 1] = child
        end
    end
    return results
end

-- Helper: get text content of a node
local function get_text(node)
    if not node then
        return nil
    end
    return node._text
end

-- Helper: recursively convert parsed XML node to a Lua table
local function xml_to_table(node)
    if not node then
        return nil
    end

    local result = {}

    -- Add attributes
    if node._attr then
        for k, v in pairs(node._attr) do
            result["@" .. k] = v
        end
    end

    -- Process children
    if node._children and #node._children > 0 then
        for _, child in ipairs(node._children) do
            local child_name = child._name:match(":(.+)$") or child._name
            local child_val

            if child._children and #child._children > 0 then
                child_val = xml_to_table(child)
            else
                child_val = get_text(child) or ""
            end

            -- Handle repeated elements as arrays
            if result[child_name] then
                if type(result[child_name]) ~= "table" or result[child_name][1] == nil then
                    result[child_name] = { result[child_name] }
                end
                table.insert(result[child_name], child_val)
            else
                result[child_name] = child_val
            end
        end
    elseif node._text then
        return node._text
    end

    return result
end

-- Extract SOAP body from envelope
local function extract_soap_body(root)
    if not root then
        return nil, "no root element"
    end

    -- Find Envelope (with or without namespace prefix)
    local envelope = root
    local envelope_name = envelope._name:match(":(.+)$") or envelope._name
    if envelope_name ~= "Envelope" then
        return nil, "root element is not a SOAP Envelope"
    end

    -- Find Body
    local body = find_child(envelope, "Body")
    if not body then
        return nil, "no SOAP Body found"
    end

    -- Find Header (optional)
    local header = find_child(envelope, "Header")

    return body, nil, header
end

-- Main request handler
local function handle_request()
    ngx.req.read_body()
    local body = ngx.req.get_body_data()

    if not body then
        -- Body might be in a temp file for large requests
        local file_path = ngx.req.get_body_file()
        if file_path then
            local f = io.open(file_path, "r")
            if f then
                body = f:read("*a")
                f:close()
            end
        end
    end

    if not body or body == "" then
        ngx.status = 400
        ngx.header["Content-Type"] = "application/xml"
        ngx.say([[<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultcode>soap:Client</faultcode><faultstring>Empty request body</faultstring></soap:Fault></soap:Body></soap:Envelope>]])
        return ngx.exit(400)
    end

    -- Enforce a maximum request size to prevent resource exhaustion
    local max_body_size = 1048576 -- 1 MB
    if #body > max_body_size then
        ngx.status = 413
        ngx.header["Content-Type"] = "application/xml"
        ngx.say([[<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultcode>soap:Client</faultcode><faultstring>Request body too large</faultstring></soap:Fault></soap:Body></soap:Envelope>]])
        return ngx.exit(413)
    end

    -- Parse the XML
    local root, err = parse_xml(body)
    if not root then
        ngx.status = 400
        ngx.header["Content-Type"] = "application/xml"
        ngx.say(string.format(
            [[<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultcode>soap:Client</faultcode><faultstring>XML parse error: %s</faultstring></soap:Fault></soap:Body></soap:Envelope>]],
            err
        ))
        return ngx.exit(400)
    end

    -- Extract SOAP body and optional header
    local soap_body, soap_err, soap_header = extract_soap_body(root)
    if not soap_body then
        ngx.status = 400
        ngx.header["Content-Type"] = "application/xml"
        ngx.say(string.format(
            [[<?xml version="1.0"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/"><soap:Body><soap:Fault><faultcode>soap:Client</faultcode><faultstring>SOAP error: %s</faultstring></soap:Fault></soap:Body></soap:Envelope>]],
            soap_err
        ))
        return ngx.exit(400)
    end

    -- Convert SOAP body to a Lua table for processing
    local request_data = xml_to_table(soap_body)

    -- Extract SOAP header data if present
    local header_data = nil
    if soap_header then
        header_data = xml_to_table(soap_header)
    end

    -- Determine the SOAP action from the first child of Body
    local operation = nil
    if soap_body._children and #soap_body._children > 0 then
        local op_node = soap_body._children[1]
        operation = op_node._name:match(":(.+)$") or op_node._name
    end

    -- Log the parsed request for downstream processing
    local result = {
        operation = operation,
        header = header_data,
        body = request_data,
    }

    -- Store parsed data in ngx.ctx for downstream phases
    ngx.ctx.soap_request = result

    -- Return JSON representation for demonstration
    ngx.status = 200
    ngx.header["Content-Type"] = "application/json"
    local json_out = cjson.encode(result)
    ngx.say(json_out or '{"error":"failed to encode response"}')
end

handle_request()