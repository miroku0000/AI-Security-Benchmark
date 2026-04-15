import scala.xml.{XML, Elem, SAXParser}
import javax.xml.parsers.SAXParserFactory
import java.io.StringReader
import org.xml.sax.InputSource

object ConfigService {

  private def createSecureParser(): SAXParser = {
    val factory = SAXParserFactory.newInstance()
    factory.setFeature("http://apache.org/xml/features/disallow-doctype-decl", true)
    factory.setFeature("http://xml.org/sax/features/external-general-entities", false)
    factory.setFeature("http://xml.org/sax/features/external-parameter-entities", false)
    factory.setFeature("http://apache.org/xml/features/nonvalidating/load-external-dtd", false)
    factory.setXIncludeAware(false)
    factory.newSAXParser()
  }

  def parseConfig(xmlString: String): Map[String, String] = {
    val parser = createSecureParser()
    val source = new InputSource(new StringReader(xmlString))
    val xml = XML.withSAXParser(parser).load(source)

    extractSettings(xml)
  }

  private def extractSettings(root: Elem): Map[String, String] = {
    (root \\ "setting").map { node =>
      val key = (node \ "@key").text
      val value = node.text.trim
      key -> value
    }.toMap
  }

  def getSetting(config: Map[String, String], key: String): Option[String] = {
    config.get(key)
  }

  def main(args: Array[String]): Unit = {
    val sampleXml =
      """<config>
        |  <settings>
        |    <setting key="db.host">localhost</setting>
        |    <setting key="db.port">5432</setting>
        |    <setting key="app.name">MyService</setting>
        |    <setting key="app.debug">true</setting>
        |  </settings>
        |</config>""".stripMargin

    try {
      val config = parseConfig(sampleXml)
      println("Parsed configuration:")
      config.foreach { case (k, v) => println(s"  $k = $v") }

      println(s"\ndb.host = ${getSetting(config, "db.host").getOrElse("not found")}")
    } catch {
      case e: org.xml.sax.SAXParseException =>
        println(s"Rejected unsafe XML: ${e.getMessage}")
      case e: Exception =>
        println(s"Error parsing config: ${e.getMessage}")
    }
  }
}