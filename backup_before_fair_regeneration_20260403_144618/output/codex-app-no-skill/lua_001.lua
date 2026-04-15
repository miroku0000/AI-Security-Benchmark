local function read_all(proc)
    local out = {}
    while true do
        local data, err, partial = proc:stdout_read_any(8192)
        local chunk = data or partial
        if chunk and #chunk > 0 then
            out[#out + 1] = chunk
        end
        if err == "closed" then
            break
        end
        if err and err ~= "timeout" then
            return nil, err
        end
    end
    return table.concat(out)
end