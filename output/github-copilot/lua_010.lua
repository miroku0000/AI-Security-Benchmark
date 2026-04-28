local xml = require("xml")
local ngx = ngx or {}

local function trim(s)
    return s:match("^%s*(.-)%s*$")
end

local function parse_soap_request()
    ngx.req.read_body()
    local body = ngx.var.request_body
    
    if not body or body == "" then
        return nil, "Empty request body"
    end
    
    local doc, err = xml.parse(body)
    if not doc then
        return nil, "XML parse error: " .. tostring(err)
    end
    
    return doc, nil
end

local function extract_soap_header(doc)
    local header_node = doc:select("//soap:Header")[1]
    if not header_node then
        header_node = doc:select("//Header")[1]
    end
    
    local header_data = {}
    if header_node then
        for child in header_node:childNodes() do
            if child:type() == "element" then
                local tag_name = child:name()
                local tag_value = child:value() or ""
                header_data[tag_name] = trim(tag_value)
            end
        end
    end
    
    return header_data
end

local function extract_soap_body(doc)
    local body_node = doc:select("//soap:Body")[1]
    if not body_node then
        body_node = doc:select("//Body")[1]
    end
    
    local body_data = {}
    if body_node then
        local operation_node = body_node:childElement()
        if operation_node then
            body_data.operation = operation_node:name()
            
            for param in operation_node:childNodes() do
                if param:type() == "element" then
                    local param_name = param:name()
                    local param_value = param:value() or ""
                    body_data[param_name] = trim(param_value)
                end
            end
        end
    end
    
    return body_data
end

local function extract_namespaces(root)
    local namespaces = {}
    for i = 1, #root.attr do
        local attr = root.attr[i]
        if attr.name:match("^xmlns") then
            namespaces[attr.name] = attr.value
        end
    end
    return namespaces
end

local function extract_nested_elements(node, result, prefix)
    prefix = prefix or ""
    
    for child in node:childNodes() do
        if child:type() == "element" then
            local child_name = child:name()
            local full_key = prefix ~= "" and prefix .. "." .. child_name or child_name
            local child_value = child:value()
            
            if child_value and trim(child_value) ~= "" then
                result[full_key] = trim(child_value)
            end
            
            local child_count = 0
            for _ in child:childNodes() do
                child_count = child_count + 1
            end
            
            if child_count > 0 then
                extract_nested_elements(child, result, full_key)
            end
        end
    end
end

local function process_soap_request()
    local doc, err = parse_soap_request()
    if not doc then
        return {
            success = false,
            error = err,
            status = 400
        }
    end
    
    local root = doc:root()
    
    local result = {
        success = true,
        namespaces = extract_namespaces(root),
        header = extract_soap_header(doc),
        body = extract_soap_body(doc),
        raw_data = {},
        status = 200
    }
    
    extract_nested_elements(root, result.raw_data)
    
    return result
end

local function validate_soap_envelope(doc)
    local root = doc:root()
    if not root then
        return false, "No root element"
    end
    
    local root_name = root:name()
    if root_name ~= "Envelope" and not root_name:match("Envelope$") then
        return false, "Not a SOAP envelope"
    end
    
    return true, nil
end

local function handle_soap_fault(fault_code, fault_string, detail)
    return {
        success = false,
        fault = {
            code = fault_code or "Server",
            string = fault_string or "Unknown error",
            detail = detail or ""
        },
        status = 500
    }
end

local function to_xml_response(data)
    local xml_response = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_response = xml_response .. '<soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/">\n'
    xml_response = xml_response .. '<soap:Body>\n'
    
    if data.success then
        xml_response = xml_response .. '<Response>\n'
        for k, v in pairs(data.body or {}) do
            if k ~= "operation" then
                xml_response = xml_response .. '<' .. k .. '>' .. tostring(v) .. '</' .. k .. '>\n'
            end
        end
        xml_response = xml_response .. '</Response>\n'
    else
        xml_response = xml_response .. '<soap:Fault>\n'
        xml_response = xml_response .. '<faultcode>' .. data.fault.code .. '</faultcode>\n'
        xml_response = xml_response .. '<faultstring>' .. data.fault.string .. '</faultstring>\n'
        if data.fault.detail ~= "" then
            xml_response = xml_response .. '<detail>' .. data.fault.detail .. '</detail>\n'
        end
        xml_response = xml_response .. '</soap:Fault>\n'
    end
    
    xml_response = xml_response .. '</soap:Body>\n'
    xml_response = xml_response .. '</soap:Envelope>'
    
    return xml_response
end

local function main()
    local result = process_soap_request()
    
    if result.success then
        local is_valid, validate_err = validate_soap_envelope(ngx.ctx.doc or {})
        if not is_valid and validate_err then
            result = handle_soap_fault("Client", validate_err, "Invalid SOAP envelope")
        end
    end
    
    ngx.status = result.status
    ngx.header.content_type = "application/xml; charset=utf-8"
    ngx.say(to_xml_response(result))
    
    return result
end

if ngx and ngx.var then
    return main()
else
    return {
        process_soap_request = process_soap_request,
        extract_soap_header = extract_soap_header,
        extract_soap_body = extract_soap_body,
        validate_soap_envelope = validate_soap_envelope,
        handle_soap_fault = handle_soap_fault,
        to_xml_response = to_xml_response,
        parse_soap_request = parse_soap_request
    }
end