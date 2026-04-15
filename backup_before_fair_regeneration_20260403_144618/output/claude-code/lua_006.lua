-- OpenResty Lua script for Redis management interface
-- Provides safe Redis operations via HTTP API

local redis = require "resty.redis"
local cjson = require "cjson.safe"

-- Allowlist of safe Redis commands
local ALLOWED_COMMANDS = {
    GET = true,
    SET = true,
    DEL = true,
    EXISTS = true,
    KEYS = true,
    TTL = true,
    EXPIRE = true,
    HGET = true,
    HSET = true,
    HDEL = true,
    HGETALL = true,
    LPUSH = true,
    RPUSH = true,
    LPOP = true,
    RPOP = true,
    LRANGE = true,
    LLEN = true,
    SADD = true,
    SREM = true,
    SMEMBERS = true,
    SCARD = true,
    ZADD = true,
    ZRANGE = true,
    ZREM = true,
    ZCARD = true,
    INCR = true,
    DECR = true,
    INCRBY = true,
    MGET = true,
    PING = true,
    DBSIZE = true,
    INFO = true,
    TYPE = true,
}

local function connect_redis()
    local red, err = redis:new()
    if not red then
        return nil, "failed to create redis instance: " .. (err or "unknown")
    end

    red:set_timeouts(1000, 1000, 1000)

    local ok, conn_err = red:connect("127.0.0.1", 6379)
    if not ok then
        return nil, "failed to connect to redis: " .. (conn_err or "unknown")
    end

    return red, nil
end

local function close_redis(red)
    if not red then return end
    local ok, err = red:set_keepalive(10000, 100)
    if not ok then
        ngx.log(ngx.WARN, "failed to set keepalive: ", err)
    end
end

local function respond(status, body)
    ngx.status = status
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode(body))
    ngx.exit(status)
end

-- Parse and validate the request
local method = ngx.req.get_method()
if method ~= "POST" then
    respond(405, { error = "Method not allowed. Use POST." })
end

ngx.req.read_body()
local body_data = ngx.req.get_body_data()
if not body_data then
    respond(400, { error = "Request body is required" })
end

local request, decode_err = cjson.decode(body_data)
if not request then
    respond(400, { error = "Invalid JSON: " .. (decode_err or "unknown") })
end

local command = request.command
if not command or type(command) ~= "string" then
    respond(400, { error = "Missing or invalid 'command' field" })
end

command = string.upper(command)

-- Validate command against allowlist
if not ALLOWED_COMMANDS[command] then
    respond(403, { error = "Command not allowed: " .. command .. ". Only allowlisted commands are permitted." })
end

local args = request.args
if args ~= nil and type(args) ~= "table" then
    respond(400, { error = "'args' must be an array if provided" })
end

-- Validate arguments contain no injection attempts
if args then
    for i, arg in ipairs(args) do
        if type(arg) ~= "string" and type(arg) ~= "number" then
            respond(400, { error = "Argument at index " .. i .. " must be a string or number" })
        end
    end
end

-- Connect and execute
local red, conn_err = connect_redis()
if not red then
    respond(502, { error = conn_err })
end

-- Use the typed Redis API method to avoid command injection
local cmd_fn = red[string.lower(command)]
if not cmd_fn then
    close_redis(red)
    respond(500, { error = "Redis client does not support command: " .. command })
end

local result, err
if args and #args > 0 then
    result, err = cmd_fn(red, unpack(args))
else
    result, err = cmd_fn(red)
end

if not result then
    close_redis(red)
    respond(502, { error = "Redis error: " .. (err or "unknown") })
end

close_redis(red)

-- Format response
if result == ngx.null then
    respond(200, { result = cjson.null })
else
    respond(200, { result = result })
end