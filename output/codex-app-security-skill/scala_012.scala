import com.sun.net.httpserver.{HttpExchange, HttpHandler, HttpServer}
import java.io.{ByteArrayOutputStream, InputStream, OutputStream}
import java.net.InetSocketAddress
import java.nio.charset.StandardCharsets
import java.util.concurrent.Executors
import javax.xml.XMLConstants
import javax.xml.parsers.SAXParserFactory
import org.xml.sax.{InputSource, SAXException}
import scala.jdk.CollectionConverters._
import scala.util.control.NonFatal
import scala.xml.{Elem, Node, XML}