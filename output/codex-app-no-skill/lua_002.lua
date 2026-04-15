local function json_error(status, message)
    ngx.status = status
    ngx.header["Content-Type"] = "application/json"
    ngx.say(cjson.encode({
        error = message
    }))
    return ngx.exit(status)
end