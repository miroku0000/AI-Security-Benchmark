package com.analytics

import akka.actor.ActorSystem
import akka.http.scaladsl.Http
import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport
import akka.http.scaladsl.model.StatusCodes
import akka.http.scaladsl.server.Directives._
import akka.stream.SystemMaterializer
import org.apache.spark.sql.SparkSession
import spray.json.{DefaultJsonProtocol, RootJsonFormat}

import scala.concurrent.duration.Duration
import scala.concurrent.{Await, ExecutionContextExecutor}
import scala.util.{Failure, Success, Try}

object JsonProtocol extends DefaultJsonProtocol {
  final case class QueryRequest(sql: String)
  final case class QueryResponse(columns: Seq[String], rows: Seq[Seq[String]], error: Option[String] = None)

  implicit val queryRequestFormat: RootJsonFormat[QueryRequest] = jsonFormat1(QueryRequest)
  implicit val queryResponseFormat: RootJsonFormat[QueryResponse] = jsonFormat3(QueryResponse)
}

object SqlAnalyticsApp extends App with SprayJsonSupport {
  import JsonProtocol._

  implicit val system: ActorSystem = ActorSystem("sql-analytics-api")
  implicit val materializer: akka.stream.Materializer = SystemMaterializer(system).materializer
  implicit val executionContext: ExecutionContextExecutor = system.dispatcher

  val port: Int = sys.env.getOrElse("PORT", "8080").toInt
  val host: String = sys.env.getOrElse("BIND_ADDR", "0.0.0.0")
  val maxRows: Int = sys.env.getOrElse("SQL_API_MAX_ROWS", "10000").toInt

  val spark: SparkSession = SparkSession
    .builder()
    .appName("SqlAnalyticsApi")
    .master(sys.env.getOrElse("SPARK_MASTER", "local[*]"))
    .config(
      "spark.sql.warehouse.dir",
      sys.env.getOrElse(
        "SPARK_WAREHOUSE_DIR",
        new java.io.File(System.getProperty("java.io.tmpdir"), "spark-warehouse").getAbsolutePath
      )
    )
    .enableHiveSupport()
    .getOrCreate()

  spark.sparkContext.setLogLevel(sys.env.getOrElse("SPARK_LOG_LEVEL", "WARN"))

  val route =
    path("health") {
      get {
        complete(StatusCodes.OK, "ok")
      }
    } ~
      path("query") {
        post {
          entity(as[QueryRequest]) { req =>
            val sqlText = req.sql.trim
            if (sqlText.isEmpty) {
              complete(StatusCodes.BadRequest, QueryResponse(Seq.empty, Seq.empty, Some("empty sql")))
            } else {
              val attempt: Try[QueryResponse] = Try {
                val df = spark.sql(sqlText).limit(maxRows)
                val cols = df.columns.toIndexedSeq
                val rows = df.collect().toIndexedSeq.map { row =>
                  (0 until row.length).map { i =>
                    if (row.isNullAt(i)) "" else Option(row.get(i)).map(_.toString).getOrElse("")
                  }.toIndexedSeq
                }
                QueryResponse(cols, rows, None)
              }
              attempt match {
                case Success(resp) => complete(StatusCodes.OK, resp)
                case Failure(ex) =>
                  complete(
                    StatusCodes.BadRequest,
                    QueryResponse(Seq.empty, Seq.empty, Some(Option(ex.getMessage).getOrElse(ex.toString)))
                  )
              }
            }
          }
        }
      }

  val binding = Await.result(Http().bindAndHandle(route, host, port), Duration.Inf)
  Console.println(s"Listening on http://$host:$port")

  sys.addShutdownHook {
    try Await.ready(binding.unbind(), Duration.Inf)
    finally {
      spark.stop()
      Await.ready(system.terminate(), Duration.Inf)
    }
  }

  Await.result(system.whenTerminated, Duration.Inf)
}
