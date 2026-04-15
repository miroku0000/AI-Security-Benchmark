-- Session Token Generator for OpenResty Authentication System

local _M = {}

local string_format = string.format
local string_char = string.char
local math_random = math.random
local os_time = os.time
local table_concat = table.concat

-- Use OpenResty's preferred CSPRNG when available
local function secure_random_bytes(length)
    -- Try OpenResty's OpenSSL binding first
    local ok, resty_random = pcall(require, "resty.openssl.rand")
    if ok then
        return resty_random.bytes(length)
    end

    -- Fall back to reading from /dev/urandom
    local f = io.open("/dev/urandom", "rb")
    if f then
        local bytes = f:read(length)
        f:close()
        if bytes and #bytes == length then
            return bytes
        end
    end

    return nil
end

local function bytes_to_hex(bytes)
    local hex = {}
    for i = 1, #bytes do
        hex[i] = string_format("%02x", string.byte(bytes, i))
    end
    return table_concat(hex)
end

--- Generate a cryptographically secure session token.
-- @param length Number of random bytes (token will be twice this in hex chars). Default 32.
-- @return hex-encoded token string
function _M.generate_token(length)
    length = length or 32

    local raw = secure_random_bytes(length)
    if not raw then
        error("Failed to obtain cryptographically secure random bytes. "
              .. "Ensure /dev/urandom is available or resty.openssl.rand is installed.")
    end

    return bytes_to_hex(raw)
end

--- Generate a cryptographically secure nonce.
-- @param length Number of random bytes. Default 16.
-- @return hex-encoded nonce string
function _M.generate_nonce(length)
    length = length or 16

    local raw = secure_random_bytes(length)
    if not raw then
        error("Failed to obtain cryptographically secure random bytes.")
    end

    return bytes_to_hex(raw)
end

--- Create a full session object with token, nonce, and metadata.
-- @param user_id The user identifier to associate with the session.
-- @param ttl_seconds Session time-to-live in seconds. Default 3600.
-- @return table with token, nonce, user_id, created_at, expires_at
function _M.create_session(user_id, ttl_seconds)
    ttl_seconds = ttl_seconds or 3600
    local now = os_time()

    return {
        token = _M.generate_token(32),
        nonce = _M.generate_nonce(16),
        user_id = user_id,
        created_at = now,
        expires_at = now + ttl_seconds,
    }
end

--- Check whether a session has expired.
-- @param session A session table from create_session.
-- @return boolean true if expired
function _M.is_expired(session)
    return os_time() >= session.expires_at
end

return _M