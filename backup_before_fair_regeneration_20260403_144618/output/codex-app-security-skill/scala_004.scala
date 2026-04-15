import com.sun.net.httpserver.{HttpExchange, HttpHandler, HttpServer}
import java.io.{BufferedReader, InputStreamReader, OutputStream}
import java.net.{InetSocketAddress, URLDecoder}
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import scala.collection.JavaConverters._
import scala.concurrent.duration._
import scala.concurrent.{Await, ExecutionContext, Future, blocking}
import scala.sys.process.{Process => SysProcess, ProcessLogger}