local commands = {
    reload_nginx = function()
        return shell_quote(NGINX_BIN) .. " -s reload"
    end,
    restart_service = function()
        local unit = ngx.var.arg_service
        if not is_safe_unit_name(unit) then
            return nil, "invalid_service"
        end
        return shell_quote(SYSTEMCTL) .. " restart -- " .. shell_quote(unit)
    end,
    start_service = function()
        local unit = ngx.var.arg_service
        if not is_safe_unit_name(unit) then
            return nil, "invalid_service"
        end
        return shell_quote(SYSTEMCTL) .. " start -- " .. shell_quote(unit)
    end,
    stop_service = function()
        local unit = ngx.var.arg_service
        if not is_safe_unit_name(unit) then
            return nil, "invalid_service"
        end
        return shell_quote(SYSTEMCTL) .. " stop -- " .. shell_quote(unit)
    end,
}