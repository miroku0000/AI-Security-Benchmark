local function children_to_table(node)
    local out = {}
    local children = node:get_children() or {}
    for _, child in ipairs(children) do
        local name = local_name(child:name())
        if name then
            local value = node_text(child)
            if out[name] == nil then
                out[name] = value
            elseif type(out[name]) == "table" then
                table.insert(out[name], value)
            else
                out[name] = { out[name], value }
            end
        end
    end
    return out
end