-- OpenResty Lua access control script
-- Place in nginx config: access_by_lua_file /path/to/openresty_access.lua;

local cjson = require "cjson"

-- Configuration
local AUTH_SECRET = os.getenv("AUTH_SECRET") or error("AUTH_SECRET environment variable is required")
local TOKEN_HEADER = "Authorization"

-- Define role hierarchy and endpoint permissions
local role_permissions = {
    admin = { "/admin", "/api", "/dashboard", "/reports", "/settings" },
    editor = { "/api", "/dashboard", "/reports" },
    viewer = { "/api", "/dashboard" },
}

-- Endpoints that do not require authentication
local public_endpoints = {
    "/health",
    "/login",
    "/public",
}

-- Check if a URI matches any entry in a list using exact prefix matching
local function uri_matches(uri, endpoints)
    for _, endpoint in ipairs(endpoints) do
        if uri == endpoint or string.sub(uri, 1, #endpoint + 1) == endpoint .. "/" then
            return true
        end
    end
    return false
end

-- Decode and validate a Bearer token (assumes base64-encoded JSON payload)
local function decode_token(auth_header)
    if not auth_header then
        return nil, "missing Authorization header"
    end

    local token = string.match(auth_header, "^Bearer%s+(.+)$")
    if not token then
        return nil, "malformed Authorization header"
    end

    -- Split token into parts (header.payload.signature)
    local parts = {}
    for part in string.gmatch(token, "[^%.]+") do
        parts[#parts + 1] = part
    end

    if #parts ~= 3 then
        return nil, "invalid token format"
    end

    -- Verify signature using HMAC-SHA256
    local hmac = require "resty.hmac"
    local h = hmac:new(AUTH_SECRET, hmac.ALGOS.SHA256)
    if not h then
        return nil, "failed to initialize HMAC"
    end

    local signing_input = parts[1] .. "." .. parts[2]
    h:update(signing_input)
    local expected_sig = h:final()

    local ngx_decode_base64 = ngx.decode_base64
    local provided_sig = ngx_decode_base64(parts[3])

    if not provided_sig or #expected_sig ~= #provided_sig then
        return nil, "invalid token signature"
    end

    -- Constant-time comparison to prevent timing attacks
    local diff = 0
    for i = 1, #expected_sig do
        diff = bit.bor(diff, bit.bxor(string.byte(expected_sig, i), string.byte(provided_sig, i)))
    end
    if diff ~= 0 then
        return nil, "invalid token signature"
    end

    -- Decode payload
    local payload_json = ngx_decode_base64(parts[2])
    if not payload_json then
        return nil, "invalid token payload encoding"
    end

    local ok, payload = pcall(cjson.decode, payload_json)
    if not ok or type(payload) ~= "table" then
        return nil, "invalid token payload"
    end

    -- Check token expiration
    if payload.exp and payload.exp < ngx.time() then
        return nil, "token expired"
    end

    return payload, nil
end

-- Main access control logic
local uri = ngx.var.uri

-- Allow public endpoints without authentication
if uri_matches(uri, public_endpoints) then
    return
end

-- Extract and validate authentication token
local auth_header = ngx.req.get_headers()[TOKEN_HEADER]
local claims, err = decode_token(auth_header)

if not claims then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "application/json"
    ngx.header["WWW-Authenticate"] = 'Bearer error="invalid_token"'
    ngx.say(cjson.encode({ error = "unauthorized", message = err }))
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

-- Validate required claims
local user_role = claims.role
local user_id = claims.sub

if not user_role or not user_id then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({ error = "unauthorized", message = "missing required token claims" }))
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

-- Validate role is a known role (prevent injection of arbitrary role strings)
if not role_permissions[user_role] then
    ngx.status = ngx.HTTP_FORBIDDEN
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({ error = "forbidden", message = "unknown role" }))
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

-- Check if the user's role grants access to the requested URI
local allowed_prefixes = role_permissions[user_role]
if not uri_matches(uri, allowed_prefixes) then
    ngx.status = ngx.HTTP_FORBIDDEN
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({ error = "forbidden", message = "insufficient permissions" }))
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end

-- Set upstream headers with validated user info
ngx.req.set_header("X-User-ID", user_id)
ngx.req.set_header("X-User-Role", user_role)
