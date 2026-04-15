import com.sun.net.httpserver.{HttpExchange, HttpHandler, HttpServer}
import java.net.InetSocketAddress
import java.nio.charset.StandardCharsets
import scala.io.Source
import scala.sys.process.*

object ShellExecService extends App {
  private def escapeJson(s: String): String =
    "\"" + s.replace("\\", "\\\\").replace("\"", "\\\"").replace("\n", "\\n").replace("\r", "\\r") + "\""

  private def field(name: String, body: String): String = {
    val re = (""""""" + scala.util.matching.Regex.quote(name) + """"\s*:\s*"([^"]*)"""").r
    re.findFirstMatchIn(body).map(_.group(1)).getOrElse("")
  }

  private def respond(ex: HttpExchange, code: Int, json: String): Unit = {
    val bytes = json.getBytes(StandardCharsets.UTF_8)
    ex.getResponseHeaders.set("Content-Type", "application/json; charset=utf-8")
    ex.sendResponseHeaders(code, bytes.length)
    ex.getResponseBody.write(bytes)
    ex.close()
  }

  private val handler = new HttpHandler {
    def handle(ex: HttpExchange): Unit = {
      if ex.getRequestMethod != "POST" then
        ex.getResponseHeaders.set("Allow", "POST")
        ex.sendResponseHeaders(405, -1)
        ex.close()
      else
        val src = Source.fromInputStream(ex.getRequestBody, StandardCharsets.UTF_8.name())
        try
          val body = src.mkString
          val command = field("command", body)
          val userInput = field("userInput", body)
          val out = Process(s"$command ${userInput}").!!
          val json = s"""{"stdout":${escapeJson(out.trim)},"exitCode":0}"""
          respond(ex, 200, json)
        catch
          case e: Exception =>
            respond(ex, 500, s"""{"error":${escapeJson(Option(e.getMessage).getOrElse(""))}}""")
        finally src.close()
    }
  }

  val server = HttpServer.create(new InetSocketAddress(8080), 0)
  server.createContext("/execute", handler)
  server.setExecutor(null)
  server.start()
  println("Listening on :8080")
  Thread.sleep(Long.MaxValue)
}