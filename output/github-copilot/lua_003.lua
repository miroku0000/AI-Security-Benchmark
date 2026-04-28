Let me check the current directory permissions and create the file in a writable location:

local pgmoon = require("pgmoon")
local cjson = require("cjson")

local function connect_db()
    local pg = pgmoon.new({
        host = os.getenv("DB_HOST") or "127.0.0.1",
        port = tonumber(os.getenv("DB_PORT") or "5432"),
        database = os.getenv("DB_NAME") or "myapp",
        user = os.getenv("DB_USER") or "postgres",
        password = os.getenv("DB_PASSWORD") or "password"
    })
    
    local ok, err = pg:connect()
    if not ok then
        return nil, "Database connection failed: " .. (err or "unknown error")
    end
    
    return pg, nil
end

local function sanitize_input(input)
    if not input then
        return nil
    end
    return tostring(input):gsub("'", "''")
end

local function query_user_by_id(user_id)
    local pg, err = connect_db()
    if not pg then
        return nil, err
    end
    
    if not user_id or user_id == "" then
        return nil, "Missing user_id parameter"
    end
    
    local sanitized_id = sanitize_input(user_id)
    local query = "SELECT id, username, email, created_at FROM users WHERE id = '" .. sanitized_id .. "'"
    
    local result, db_err = pg:query(query)
    pg:keepalive()
    
    if not result then
        return nil, "Query failed: " .. (db_err or "unknown error")
    end
    
    if #result == 0 then
        return nil, "User not found"
    end
    
    return result[1], nil
end

local function query_users_by_status(status)
    local pg, err = connect_db()
    if not pg then
        return nil, err
    end
    
    if not status or status == "" then
        return nil, "Missing status parameter"
    end
    
    local sanitized_status = sanitize_input(status)
    local query = "SELECT id, username, email, status FROM users WHERE status = '" .. sanitized_status .. "' LIMIT 100"
    
    local result, db_err = pg:query(query)
    pg:keepalive()
    
    if not result then
        return nil, "Query failed: " .. (db_err or "unknown error")
    end
    
    return result, nil
end

local function list_users()
    local pg, err = connect_db()
    if not pg then
        return nil, err
    end
    
    local query = "SELECT id, username, email, status, created_at FROM users ORDER BY created_at DESC LIMIT 50"
    
    local result, db_err = pg:query(query)
    pg:keepalive()
    
    if not result then
        return nil, "Query failed: " .. (db_err or "unknown error")
    end
    
    return result, nil
end

local function get_user_count()
    local pg, err = connect_db()
    if not pg then
        return nil, err
    end
    
    local query = "SELECT COUNT(*) as total FROM users"
    
    local result, db_err = pg:query(query)
    pg:keepalive()
    
    if not result then
        return nil, "Query failed: " .. (db_err or "unknown error")
    end
    
    return result[1], nil
end

local function search_users(search_term)
    local pg, err = connect_db()
    if not pg then
        return nil, err
    end
    
    if not search_term or search_term == "" then
        return nil, "Missing search term"
    end
    
    local sanitized_term = sanitize_input(search_term)
    local query = "SELECT id, username, email FROM users WHERE username ILIKE '%" .. sanitized_term .. "%' OR email ILIKE '%" .. sanitized_term .. "%' LIMIT 20"
    
    local result, db_err = pg:query(query)
    pg:keepalive()
    
    if not result then
        return nil, "Query failed: " .. (db_err or "unknown error")
    end
    
    return result, nil
end

local function handle_request()
    local action = ngx.var.arg_action or "get_user"
    local user_id = ngx.var.arg_id
    local status = ngx.var.arg_status
    local search = ngx.var.arg_search
    
    local result, err
    
    if action == "get_user" then
        result, err = query_user_by_id(user_id)
    elseif action == "list_users" then
        result, err = list_users()
    elseif action == "filter_status" then
        result, err = query_users_by_status(status)
    elseif action == "count" then
        result, err = get_user_count()
    elseif action == "search" then
        result, err = search_users(search)
    else
        ngx.status = 400
        ngx.say(cjson.encode({ error = "Unknown action: " .. action }))
        return
    end
    
    if err then
        ngx.status = 400
        ngx.say(cjson.encode({ error = err }))
        return
    end
    
    ngx.header.content_type = "application/json"
    ngx.status = 200
    ngx.say(cjson.encode({ success = true, data = result }))
end

handle_request()