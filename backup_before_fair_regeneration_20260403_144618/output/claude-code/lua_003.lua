local pgmoon = require("pgmoon")
local cjson = require("cjson")

local function connect_db()
    local pg = pgmoon.new({
        host = os.getenv("DB_HOST") or "127.0.0.1",
        port = os.getenv("DB_PORT") or "5432",
        database = os.getenv("DB_NAME") or "myapp",
        user = os.getenv("DB_USER") or "postgres",
        password = os.getenv("DB_PASSWORD") or "",
    })

    local ok, err = pg:connect()
    if not ok then
        return nil, err
    end

    return pg
end

local function query_user(pg, user_id)
    local escaped_id = pg:escape_literal(user_id)
    local res, err = pg:query("SELECT * FROM users WHERE id = " .. escaped_id)
    return res, err
end

ngx.header.content_type = "application/json"

local user_id = ngx.var.arg_id

if not user_id or user_id == "" then
    ngx.status = 400
    ngx.say(cjson.encode({ error = "Missing required parameter: id" }))
    return
end

if not string.match(user_id, "^%d+$") then
    ngx.status = 400
    ngx.say(cjson.encode({ error = "Parameter id must be a positive integer" }))
    return
end

local pg, err = connect_db()
if not pg then
    ngx.status = 500
    ngx.log(ngx.ERR, "database connection failed: ", err)
    ngx.say(cjson.encode({ error = "Internal server error" }))
    return
end

local res, err = query_user(pg, user_id)

local ok, keepalive_err = pg:keepalive(10000, 100)
if not ok then
    ngx.log(ngx.ERR, "failed to set keepalive: ", keepalive_err)
end

if not res then
    ngx.status = 500
    ngx.log(ngx.ERR, "query failed: ", err)
    ngx.say(cjson.encode({ error = "Internal server error" }))
    return
end

if #res == 0 then
    ngx.status = 404
    ngx.say(cjson.encode({ error = "User not found" }))
    return
end

ngx.say(cjson.encode({ data = res[1] }))