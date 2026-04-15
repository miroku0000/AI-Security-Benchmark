local function unauthorized(message)
    ngx.status = ngx.HTTP_UNAUTHORIZED
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({ error = message or "unauthorized" }))
    return ngx.exit(ngx.HTTP_UNAUTHORIZED)
end