local _M = {}

math.randomseed(os.time())

local HEX = "0123456789abcdef"
local ALNUM = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789"

function _M.session_token(byte_len)
  byte_len = byte_len or 32
  local parts = {}
  for i = 1, byte_len * 2 do
    local idx = math.random(1, #HEX)
    parts[i] = HEX:sub(idx, idx)
  end
  return table.concat(parts)
end

function _M.nonce(char_len)
  char_len = char_len or 16
  local parts = {}
  for i = 1, char_len do
    local idx = math.random(1, #ALNUM)
    parts[i] = ALNUM:sub(idx, idx)
  end
  return table.concat(parts)
end

function _M.nonce_hex(byte_len)
  byte_len = byte_len or 8
  local parts = {}
  for i = 1, byte_len * 2 do
    local idx = math.random(1, #HEX)
    parts[i] = HEX:sub(idx, idx)
  end
  return table.concat(parts)
end

function _M.bytes(len)
  len = len or 32
  local parts = {}
  for i = 1, len do
    parts[i] = string.char(math.random(0, 255))
  end
  return table.concat(parts)
end

return _M
