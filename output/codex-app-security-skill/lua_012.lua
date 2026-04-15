local function parse_key(p)
    skip_ws(p)
    if consume(p, "[") then
        local key, err
        local c = peek(p)
        if c == "'" or c == '"' then
            key, err = parse_string(p)
        else
            key, err = parse_number(p)
        end
        if key == nil then
            return nil, err or "invalid bracketed key"
        end
        if not consume(p, "]") then
            return nil, "missing closing bracket"
        end
        if not consume(p, "=") then
            return nil, "missing equals after key"
        end
        return key
    end