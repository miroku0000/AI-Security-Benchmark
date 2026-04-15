local function respond(status, body)
  ngx.status = status
  ngx.say(cjson.encode(body))
  return ngx.exit(status)
end