import com.sun.net.httpserver.{HttpExchange, HttpHandler, HttpServer}
import java.io.{InputStream, OutputStream}
import java.net.InetSocketAddress
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import javax.xml.XMLConstants
import javax.xml.parsers.SAXParserFactory
import scala.jdk.CollectionConverters._
import scala.util.{Failure, Success, Try}
import scala.xml.{Elem, Node, XML}