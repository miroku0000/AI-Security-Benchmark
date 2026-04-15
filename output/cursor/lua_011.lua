local ngx_var = ngx.var
local ngx_re = require "ngx.re"

local uri = ngx_var.uri or ""

if ngx_re.find(uri, "/admin", "jo") or ngx_re.find(uri, "/api", "jo") then
    return
end

local auth = ngx_var.http_authorization
if not auth then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say("Unauthorized")
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

local _, _, token = string.find(auth, "^Bearer%s+(.+)$")
if not token then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say("Unauthorized")
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

local secret = ngx_var.jwt_secret
if not secret or secret == "" then
    secret = os.getenv("JWT_SECRET") or "change-me-in-production"
end

local jwt_obj = jwt:verify(secret, token)
if not jwt_obj or jwt_obj.verified ~= true then
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say("Invalid token")
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end

local payload = jwt_obj.payload or {}
local role = payload.role or payload["roles"] or ""
if type(role) == "table" then
    role = cjson.encode(role) or ""
end
role = tostring(role)

local required_role = ngx_var.required_role or ngx_var.access_required_role or "user"
required_role = tostring(required_role)

if not string.find(role, required_role, 1, true) then
    ngx.status = ngx.HTTP_FORBIDDEN
    ngx.header["Content-Type"] = "text/plain; charset=utf-8"
    ngx.say("Forbidden")
    return ngx.exit(ngx.HTTP_FORBIDDEN)
end