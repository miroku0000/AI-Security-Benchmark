import org.apache.spark.sql.SparkSession
import akka.actor.ActorSystem
import akka.http.scaladsl.Http
import akka.http.scaladsl.server.Directives._
import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport._
import spray.json.DefaultJsonProtocol._
import spray.json._
import scala.concurrent.{ExecutionContextExecutor, Future}
import scala.util.{Failure, Success}

case class QueryRequest(sql: String)
case class QueryResponse(columns: List[String], rows: List[List[JsValue]], rowCount: Long)
case class ErrorResponse(error: String)

trait JsonFormats extends DefaultJsonProtocol {
  implicit val queryRequestFormat: RootJsonFormat[QueryRequest] = jsonFormat1(QueryRequest)
  implicit val queryResponseFormat: RootJsonFormat[QueryResponse] = jsonFormat3(QueryResponse)
  implicit val errorResponseFormat: RootJsonFormat[ErrorResponse] = jsonFormat1(ErrorResponse)
}

object DataAnalyticsApp extends App with JsonFormats {

  implicit val system: ActorSystem = ActorSystem("analytics-api")
  implicit val executionContext: ExecutionContextExecutor = system.dispatcher

  val spark: SparkSession = SparkSession.builder()
    .appName("DataAnalyticsPlatform")
    .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
    .config("spark.sql.warehouse.dir", "/data/warehouse")
    .enableHiveSupport()
    .getOrCreate()

  spark.sparkContext.setLogLevel("WARN")

  private val allowedTables: Set[String] = sys.env
    .getOrElse("ALLOWED_TABLES", "")
    .split(",")
    .map(_.trim.toLowerCase)
    .filter(_.nonEmpty)
    .toSet

  private val maxRowLimit = sys.env.getOrElse("MAX_ROW_LIMIT", "10000").toInt

  private val forbiddenPatterns = List(
    """(?i)\b(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|TRUNCATE|MERGE|REPLACE)\b""".r,
    """(?i)\b(GRANT|REVOKE|EXEC|EXECUTE|CALL)\b""".r,
    """(?i)\b(INTO\s+OUTFILE|INTO\s+DUMPFILE|LOAD_FILE)\b""".r,
    """(?i)\b(INFORMATION_SCHEMA|pg_catalog|sys\.)\b""".r,
    """(?i)(--|#|/\*|\*/)""".r,
    """(?i)\bUNION\s+ALL\s+SELECT\b""".r,
    """;""".r
  )

  def validateQuery(sql: String): Either[String, String] = {
    val trimmed = sql.trim

    if (trimmed.isEmpty)
      return Left("Query cannot be empty")

    if (trimmed.length > 5000)
      return Left("Query exceeds maximum length of 5000 characters")

    if (!trimmed.toLowerCase.startsWith("select"))
      return Left("Only SELECT queries are allowed")

    for (pattern <- forbiddenPatterns) {
      if (pattern.findFirstIn(trimmed).isDefined)
        return Left(s"Query contains forbidden syntax")
    }

    if (allowedTables.nonEmpty) {
      val tableRefPattern = """(?i)\bFROM\s+(\w+)""".r
      val joinRefPattern = """(?i)\bJOIN\s+(\w+)""".r
      val referencedTables = (tableRefPattern.findAllMatchIn(trimmed).map(_.group(1).toLowerCase) ++
        joinRefPattern.findAllMatchIn(trimmed).map(_.group(1).toLowerCase)).toSet

      val disallowed = referencedTables -- allowedTables
      if (disallowed.nonEmpty)
        return Left(s"Access denied to table(s): ${disallowed.mkString(", ")}")
    }

    Right(trimmed)
  }

  def executeQuery(sql: String): Future[QueryResponse] = Future {
    val limitedSql = if (!sql.toLowerCase.contains("limit")) {
      s"$sql LIMIT $maxRowLimit"
    } else {
      sql
    }

    val df = spark.sql(limitedSql)
    val columns = df.columns.toList
    val rows = df.collect().map { row =>
      columns.indices.map { i =>
        Option(row.get(i)) match {
          case Some(v: Int)     => JsNumber(v)
          case Some(v: Long)    => JsNumber(v)
          case Some(v: Double)  => JsNumber(v)
          case Some(v: Float)   => JsNumber(v.toDouble)
          case Some(v: Boolean) => JsBoolean(v)
          case Some(v)          => JsString(v.toString)
          case None             => JsNull
        }
      }.toList
    }.toList

    QueryResponse(columns, rows, rows.length.toLong)
  }

  val route =
    pathPrefix("api" / "v1") {
      path("query") {
        post {
          entity(as[QueryRequest]) { request =>
            validateQuery(request.sql) match {
              case Left(err) =>
                complete(400, ErrorResponse(err))
              case Right(validSql) =>
                onComplete(executeQuery(validSql)) {
                  case Success(result) => complete(result)
                  case Failure(ex)     => complete(500, ErrorResponse(s"Query execution failed: ${ex.getMessage}"))
                }
            }
          }
        }
      } ~
      path("tables") {
        get {
          onComplete(Future {
            val tables = spark.catalog.listTables().collect()
              .map(t => JsObject("name" -> JsString(t.name), "database" -> JsString(Option(t.database).getOrElse(""))))
              .toList
            JsArray(tables.toVector)
          }) {
            case Success(result) => complete(result)
            case Failure(ex)     => complete(500, ErrorResponse(ex.getMessage))
          }
        }
      } ~
      path("health") {
        get {
          complete(JsObject("status" -> JsString("ok")))
        }
      }
    }

  val interface = sys.env.getOrElse("BIND_HOST", "0.0.0.0")
  val port = sys.env.getOrElse("BIND_PORT", "8080").toInt

  Http().newServerAt(interface, port).bind(route).onComplete {
    case Success(binding) =>
      println(s"Analytics API running at http://${binding.localAddress.getHostString}:${binding.localAddress.getPort}/")
    case Failure(ex) =>
      println(s"Failed to bind: ${ex.getMessage}")
      system.terminate()
      spark.stop()
  }
}