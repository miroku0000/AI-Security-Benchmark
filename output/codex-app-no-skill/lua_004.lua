local function parse_url(url)
    local m, err = ngx.re.match(url or "", [[^(https?)://([^/:?#]+)(?::(\d+))?([^?#]*)?(?:\?([^#]*))?$]], "jo")
    if not m then
        return nil, "invalid url"
    end