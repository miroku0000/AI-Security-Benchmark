local function b64url_to_b64(s)
    if type(s) ~= "string" or s == "" then
        return nil
    end