local function secure_bytes(n)
    local bytes, err = random.bytes(n, true)
    if not bytes then
        return nil, "failed to generate secure random bytes: " .. (err or "unknown error")
    end
    return bytes
end