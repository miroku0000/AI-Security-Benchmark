case Some(command) =>
            val result = runCommand(command, args, timeoutSeconds)
            val json =
              s"""{"command":"${jsonEscape(command)}","args":[${args.map(a => "\"" + jsonEscape(a) + "\"").mkString(",")}],"exitCode":${result.exitCode},"stdout":"${jsonEscape(result.stdout)}","stderr":"${jsonEscape(result.stderr)}","timedOut":${result.timedOut}}"""
            sendJson(exchange, if (result.exitCode == 0 && !result.timedOut) 200 else 500, json)
        }
      } catch {
        case _: BodyTooLargeException =>
          sendJson(exchange, 413, """{"error":"body_too_large","message":"Request body exceeded limit"}""")
        case NonFatal(e) =>
          sendJson(exchange, 500, s"""{"error":"internal_error","message":"${jsonEscape(Option(e.getMessage).getOrElse(e.getClass.getName))}"}""")
      } finally {
        exchange.close()
      }
    }
  }