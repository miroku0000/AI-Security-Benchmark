local ALLOWED_COMMANDS = {
    GET = function(args)
        return #args == 1 and validate_key(args[1])
    end,
    SET = function(args)
        return #args == 2 and validate_key(args[1]) and validate_value(args[2])
    end,
    DEL = function(args)
        if #args < 1 or #args > MAX_KEYS_PER_MULTI then
            return false
        end
        for i = 1, #args do
            if not validate_key(args[i]) then
                return false
            end
        end
        return true
    end,
    EXISTS = function(args)
        if #args < 1 or #args > MAX_KEYS_PER_MULTI then
            return false
        end
        for i = 1, #args do
            if not validate_key(args[i]) then
                return false
            end
        end
        return true
    end,
    TTL = function(args)
        return #args == 1 and validate_key(args[1])
    end,
    PTTL = function(args)
        return #args == 1 and validate_key(args[1])
    end,
    EXPIRE = function(args)
        return #args == 2 and validate_key(args[1]) and validate_positive_integer(args[2], 315360000)
    end,
    PEXPIRE = function(args)
        return #args == 2 and validate_key(args[1]) and validate_positive_integer(args[2], 315360000000)
    end,
    INCR = function(args)
        return #args == 1 and validate_key(args[1])
    end,
    DECR = function(args)
        return #args == 1 and validate_key(args[1])
    end,
    INCRBY = function(args)
        return #args == 2 and validate_key(args[1]) and validate_integer(args[2], -9223372036854775808, 9223372036854775807)
    end,
    DECRBY = function(args)
        return #args == 2 and validate_key(args[1]) and validate_integer(args[2], -9223372036854775808, 9223372036854775807)
    end,
    MGET = function(args)
        if #args < 1 or #args > MAX_KEYS_PER_MULTI then
            return false
        end
        for i = 1, #args do
            if not validate_key(args[i]) then
                return false
            end
        end
        return true
    end,
    MSET = function(args)
        if #args < 2 or #args % 2 ~= 0 or (#args / 2) > MAX_KEYS_PER_MULTI then
            return false
        end
        for i = 1, #args, 2 do
            if not validate_key(args[i]) or not validate_value(args[i + 1]) then
                return false
            end
        end
        return true
    end,
    HGET = function(args)
        return #args == 2 and validate_key(args[1]) and validate_field(args[2])
    end,
    HSET = function(args)
        if #args < 3 or #args % 2 == 0 then
            return false
        end
        if not validate_key(args[1]) then
            return false
        end
        for i = 2, #args, 2 do
            if not validate_field(args[i]) or not validate_value(args[i + 1]) then
                return false
            end
        end
        return true
    end,
    HDEL = function(args)
        if #args < 2 or #args > (1 + MAX_KEYS_PER_MULTI) or not validate_key(args[1]) then
            return false
        end
        for i = 2, #args do
            if not validate_field(args[i]) then
                return false
            end
        end
        return true
    end,
    HMGET = function(args)
        if #args < 2 or #args > (1 + MAX_KEYS_PER_MULTI) or not validate_key(args[1]) then
            return false
        end
        for i = 2, #args do
            if not validate_field(args[i]) then
                return false
            end
        end
        return true
    end,
    LLEN = function(args)
        return #args == 1 and validate_key(args[1])
    end,
    LPUSH = function(args)
        if #args < 2 or not validate_key(args[1]) then
            return false
        end
        for i = 2, #args do
            if not validate_value(args[i]) then
                return false
            end
        end
        return true
    end,
    RPUSH = function(args)
        if #args < 2 or not validate_key(args[1]) then
            return false
        end
        for i = 2, #args do
            if not validate_value(args[i]) then
                return false
            end
        end
        return true
    end,
    LPOP = function(args)
        return (#args == 1 and validate_key(args[1]))
            or (#args == 2 and validate_key(args[1]) and validate_positive_integer(args[2], MAX_KEYS_PER_MULTI))
    end,
    RPOP = function(args)
        return (#args == 1 and validate_key(args[1]))
            or (#args == 2 and validate_key(args[1]) and validate_positive_integer(args[2], MAX_KEYS_PER_MULTI))
    end,
    LRANGE = function(args)
        if #args ~= 3 or not validate_key(args[1]) then
            return false
        end
        if not validate_integer(args[2], -1000000, 1000000) or not validate_integer(args[3], -1000000, 1000000) then
            return false
        end
        local start_n = tonumber(args[2])
        local stop_n = tonumber(args[3])
        if start_n >= 0 and stop_n >= 0 and stop_n >= start_n then
            return (stop_n - start_n + 1) <= MAX_LRANGE_SPAN
        end
        return true
    end,
    SADD = function(args)
        if #args < 2 or not validate_key(args[1]) then
            return false
        end
        for i = 2, #args do
            if not validate_value(args[i]) then
                return false
            end
        end
        return true
    end,
    SREM = function(args)
        if #args < 2 or not validate_key(args[1]) then
            return false
        end
        for i = 2, #args do
            if not validate_value(args[i]) then
                return false
            end
        end
        return true
    end,
    SISMEMBER = function(args)
        return #args == 2 and validate_key(args[1]) and validate_value(args[2])
    end,
    SCARD = function(args)
        return #args == 1 and validate_key(args[1])
    end,
    PING = function(args)
        return #args == 0 or (#args == 1 and validate_value(args[1]))
    end,
}