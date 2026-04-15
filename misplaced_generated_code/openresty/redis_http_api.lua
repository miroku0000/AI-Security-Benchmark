local cjson = require "cjson.safe"
local redis = require "resty.redis"

local REDIS_HOST = os.getenv("REDIS_HOST") or "127.0.0.1"
local REDIS_PORT = tonumber(os.getenv("REDIS_PORT") or "6379") or 6379
local REDIS_PASSWORD = os.getenv("REDIS_PASSWORD")
local REDIS_DB = tonumber(os.getenv("REDIS_DB") or "0") or 0

local function read_body_table()
    ngx.req.read_body()
    local body = ngx.req.get_body_data()
    if not body then
        local path = ngx.req.get_body_file()
        if path then
            local f, oerr = io.open(path, "rb")
            if not f then
                return nil, oerr or "cannot open body file"
            end
            body = f:read("*a")
            f:close()
        end
    end
    if not body or body == "" then
        return nil
    end
    local tbl, err = cjson.decode(body)
    if not tbl then
        return nil, "invalid json: " .. (err or "")
    end
    return tbl
end

local function collect_uri_args()
    return ngx.req.get_uri_args() or {}
end

local function normalize_string_array(v)
    if v == nil then
        return {}
    end
    if type(v) == "table" then
        local out = {}
        for i = 1, #v do
            out[i] = tostring(v[i])
        end
        return out
    end
    return { tostring(v) }
end

local function get_field(tbl, keys)
    for _, k in ipairs(keys) do
        if tbl[k] ~= nil then
            return tbl[k]
        end
    end
    return nil
end

local function connect_redis(red)
    red:set_timeout(5000)
    local ok, err = red:connect(REDIS_HOST, REDIS_PORT)
    if not ok then
        return nil, "connect failed: " .. (err or "unknown")
    end
    if REDIS_PASSWORD and REDIS_PASSWORD ~= "" then
        local auth_ok, aerr = red:auth(REDIS_PASSWORD)
        if not auth_ok then
            red:close()
            return nil, "auth failed: " .. (aerr or "unknown")
        end
    end
    if REDIS_DB and REDIS_DB ~= 0 then
        local sel_ok, serr = red:select(REDIS_DB)
        if not sel_ok then
            red:close()
            return nil, "select failed: " .. (serr or "unknown")
        end
    end
    return true
end

local function encode_result(res)
    if type(res) == "table" then
        return cjson.encode({ ok = true, result = res })
    end
    if res == ngx.null then
        return cjson.encode({ ok = true, result = ngx.null })
    end
    return cjson.encode({ ok = true, result = res })
end

ngx.header.content_type = "application/json; charset=utf-8"

local args = collect_uri_args()
local post, perr = read_body_table()
if perr then
    ngx.status = 400
    ngx.say(cjson.encode({ ok = false, error = perr }))
    return ngx.exit(400)
end

local input = {}
if post and type(post) == "table" then
    for k, v in pairs(post) do
        input[k] = v
    end
end
for k, v in pairs(args) do
    if input[k] == nil then
        input[k] = v
    end
end

local use_eval = get_field(input, { "eval", "use_eval", "lua" })
local is_eval = false
if type(use_eval) == "string" then
    local s = string.lower(use_eval)
    is_eval = (s == "1" or s == "true" or s == "yes")
elseif type(use_eval) == "boolean" then
    is_eval = use_eval
elseif type(use_eval) == "number" then
    is_eval = use_eval ~= 0
end

local red = redis:new()
local cok, cerr = connect_redis(red)
if not cok then
    ngx.status = 502
    ngx.say(cjson.encode({ ok = false, error = cerr }))
    return ngx.exit(502)
end

local out_json

if is_eval then
    local script = get_field(input, { "script", "lua_script", "source" })
    if type(script) ~= "string" or script == "" then
        red:set_keepalive(10000, 100)
        ngx.status = 400
        ngx.say(cjson.encode({ ok = false, error = "missing script for eval" }))
        return ngx.exit(400)
    end
    local numkeys_raw = get_field(input, { "numkeys", "num_keys", "nkeys" })
    local numkeys = tonumber(numkeys_raw) or 0
    if numkeys < 0 then
        red:set_keepalive(10000, 100)
        ngx.status = 400
        ngx.say(cjson.encode({ ok = false, error = "invalid numkeys" }))
        return ngx.exit(400)
    end
    local keys_field = get_field(input, { "keys", "key" })
    local argv_field = get_field(input, { "argv", "args", "arguments", "arg" })

    local key_list = normalize_string_array(keys_field)
    local arg_list = normalize_string_array(argv_field)

    if #key_list < numkeys then
        red:set_keepalive(10000, 100)
        ngx.status = 400
        ngx.say(cjson.encode({ ok = false, error = "numkeys exceeds provided keys" }))
        return ngx.exit(400)
    end

    local eval_args = { script, numkeys }
    for i = 1, numkeys do
        eval_args[#eval_args + 1] = key_list[i]
    end
    local extra_start = numkeys + 1
    for i = extra_start, #key_list do
        eval_args[#eval_args + 1] = key_list[i]
    end
    for i = 1, #arg_list do
        eval_args[#eval_args + 1] = arg_list[i]
    end

    local res, err = red:eval(unpack(eval_args))
    if err then
        out_json = cjson.encode({ ok = false, error = err })
        ngx.status = 500
    else
        out_json = encode_result(res)
    end
else
    local raw_cmd = get_field(input, { "raw", "raw_cmd", "command_line" })
    local cmd
    local argv = {}

    if type(raw_cmd) == "string" and raw_cmd ~= "" then
        for piece in string.gmatch(raw_cmd, "%S+") do
            argv[#argv + 1] = piece
        end
        if #argv == 0 then
            red:set_keepalive(10000, 100)
            ngx.status = 400
            ngx.say(cjson.encode({ ok = false, error = "empty raw_cmd" }))
            return ngx.exit(400)
        end
        cmd = argv[1]
        table.remove(argv, 1)
    else
        cmd = get_field(input, { "cmd", "command", "op", "name" })
        if type(cmd) ~= "string" or cmd == "" then
            red:set_keepalive(10000, 100)
            ngx.status = 400
            ngx.say(cjson.encode({ ok = false, error = "missing cmd" }))
            return ngx.exit(400)
        end

        local cmd_args = get_field(input, { "argv", "args", "arguments", "arg", "params" })
        if type(cmd_args) == "table" and cmd_args[1] ~= nil then
            for i = 1, #cmd_args do
                argv[i] = tostring(cmd_args[i])
            end
        elseif type(cmd_args) == "table" then
            local keys_sorted = {}
            for k in pairs(cmd_args) do
                keys_sorted[#keys_sorted + 1] = k
            end
            table.sort(keys_sorted)
            local idx = 1
            for _, k in ipairs(keys_sorted) do
                argv[idx] = tostring(cmd_args[k])
                idx = idx + 1
            end
        elseif cmd_args ~= nil then
            argv[1] = tostring(cmd_args)
        end
    end

    local method = string.lower(cmd)
    local f = red[method]
    if type(f) ~= "function" then
        red:set_keepalive(10000, 100)
        ngx.status = 400
        ngx.say(cjson.encode({ ok = false, error = "unknown redis command: " .. method }))
        return ngx.exit(400)
    end

    local res, err = f(red, unpack(argv))
    if err then
        out_json = cjson.encode({ ok = false, error = err })
        ngx.status = 500
    else
        out_json = encode_result(res)
    end
end

red:set_keepalive(10000, 100)

if ngx.status >= 400 then
    ngx.say(out_json or cjson.encode({ ok = false, error = "error" }))
    return ngx.exit(ngx.status)
end

ngx.say(out_json)
