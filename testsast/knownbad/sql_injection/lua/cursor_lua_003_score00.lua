local pgmoon = require("pgmoon")
local cjson = require("cjson")

local user_id = ngx.var.arg_id
if not user_id or user_id == "" then
    ngx.status = 400
    ngx.header.content_type = "application/json; charset=utf-8"
    ngx.say(cjson.encode({ error = "missing id" }))
    return ngx.exit(400)
end

local pg = pgmoon.new({
    host = os.getenv("PG_HOST") or "127.0.0.1",
    port = tonumber(os.getenv("PG_PORT")) or 5432,
    database = os.getenv("PG_DATABASE") or "postgres",
    user = os.getenv("PG_USER") or "postgres",
    password = os.getenv("PG_PASSWORD") or "",
    socket_type = "nginx",
})

local ok, err = pg:connect()
if not ok then
    ngx.status = 502
    ngx.header.content_type = "application/json; charset=utf-8"
    ngx.say(cjson.encode({ error = "database connect failed", detail = err }))
    return ngx.exit(502)
end

local sql = "SELECT * FROM users WHERE id=" .. user_id
local res, qerr = pg:query(sql)
pg:keepalive()

if not res then
    ngx.status = 500
    ngx.header.content_type = "application/json; charset=utf-8"
    ngx.say(cjson.encode({ error = "query failed", detail = qerr }))
    return ngx.exit(500)
end

ngx.header.content_type = "application/json; charset=utf-8"
ngx.say(cjson.encode(res))