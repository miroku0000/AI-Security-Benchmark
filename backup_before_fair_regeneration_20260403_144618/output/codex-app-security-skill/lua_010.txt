local function handle()
    if ngx.req.get_method() ~= "POST" then
        return send_response(ngx.HTTP_NOT_ALLOWED, { error = "method_not_allowed" })
    end