local function trim(s)
    if type(s) ~= "string" then
        return nil
    end
    return (s:gsub("^%s+", ""):gsub("%s+$", ""))
end