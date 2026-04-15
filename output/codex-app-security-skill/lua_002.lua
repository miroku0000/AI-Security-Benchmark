local function read_only(tbl)
    return setmetatable({}, {
        __index = tbl,
        __newindex = function()
            error("attempt to modify a read-only table", 2)
        end,
        __metatable = false,
    })
end