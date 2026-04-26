package com.analytics

import akka.actor.ActorSystem
import akka.http.scaladsl.Http
import akka.http.scaladsl.model._
import akka.http.scaladsl.server.Directives._
import akka.stream.ActorMaterializer
import play.api.libs.json._
import org.apache.spark.sql.{SparkSession, DataFrame}
import scala.concurrent.{ExecutionContext, Future}
import scala.util.{Try, Success, Failure}
import java.util.concurrent.ConcurrentHashMap

object SparkSqlApi {
  implicit val system: ActorSystem = ActorSystem("spark-sql-api")
  implicit val materializer: ActorMaterializer = ActorMaterializer()
  implicit val executionContext: ExecutionContext = system.dispatcher

  val spark: SparkSession = SparkSession
    .builder()
    .appName("SparkSqlApi")
    .master("local[*]")
    .config("spark.sql.adaptive.enabled", "true")
    .config("spark.sql.adaptive.coalescePartitions.enabled", "true")
    .config("spark.sql.adaptive.skewJoin.enabled", "true")
    .config("spark.sql.shuffle.partitions", "200")
    .config("spark.driver.memory", "4g")
    .config("spark.executor.memory", "4g")
    .getOrCreate()

  spark.sparkContext.setLogLevel("WARN")

  val queryCache = new ConcurrentHashMap[String, CachedQuery]()
  val maxCacheSize = 100

  case class CachedQuery(result: String, timestamp: Long)

  case class SqlRequest(query: String, cacheKey: Option[String] = None, useCache: Boolean = false)
  case class SqlResponse(success: Boolean, result: Option[String] = None, error: Option[String] = None, rowCount: Option[Long] = None, executionTimeMs: Option[Long] = None)
  case class DataLakeConfig(name: String, location: String)

  implicit val sqlRequestFormat: Format[SqlRequest] = Json.format[SqlRequest]
  implicit val sqlResponseFormat: Format[SqlResponse] = Json.format[SqlResponse]
  implicit val dataLakeConfigFormat: Format[DataLakeConfig] = Json.format[DataLakeConfig]

  def initializeSampleData(): Unit = {
    val sampleCustomers = Seq(
      (1, "Alice Johnson", "NYC", 25000.50),
      (2, "Bob Smith", "LA", 35000.75),
      (3, "Carol White", "Chicago", 45000.00),
      (4, "David Brown", "NYC", 55000.25),
      (5, "Eve Davis", "Boston", 65000.00)
    )

    val sampleOrders = Seq(
      (101, 1, 1500.00, "2024-01-15"),
      (102, 2, 2500.00, "2024-01-20"),
      (103, 1, 3000.00, "2024-02-10"),
      (104, 3, 1200.00, "2024-02-15"),
      (105, 4, 5000.00, "2024-03-01"),
      (106, 2, 2000.00, "2024-03-05"),
      (107, 5, 4500.00, "2024-03-10")
    )

    val sampleProducts = Seq(
      (1001, "Laptop", 1200.00, 15),
      (1002, "Monitor", 400.00, 45),
      (1003, "Keyboard", 120.00, 200),
      (1004, "Mouse", 50.00, 350),
      (1005, "Headphones", 180.00, 80)
    )

    val customersDF = spark.createDataFrame(sampleCustomers)
      .toDF("customer_id", "name", "city", "annual_spend")
    customersDF.createOrReplaceTempView("customers")

    val ordersDF = spark.createDataFrame(sampleOrders)
      .toDF("order_id", "customer_id", "amount", "order_date")
    ordersDF.createOrReplaceTempView("orders")

    val productsDF = spark.createDataFrame(sampleProducts)
      .toDF("product_id", "product_name", "price", "stock_quantity")
    productsDF.createOrReplaceTempView("products")
  }

  def isQuerySafe(query: String): Boolean = {
    val lowerQuery = query.toLowerCase().trim
    val unsafePatterns = List(
      "drop",
      "delete",
      "truncate",
      "alter",
      "create temporary",
      "insert",
      "update",
      "drop database",
      "drop table"
    )
    !unsafePatterns.exists(lowerQuery.contains)
  }

  def executeQuery(query: String, useCache: Boolean = false, cacheKey: Option[String] = None): Future[SqlResponse] = {
    Future {
      val startTime = System.currentTimeMillis()

      if (!isQuerySafe(query)) {
        return SqlResponse(
          success = false,
          error = Some("Query contains disallowed operations. Only SELECT queries are permitted.")
        )
      }

      if (useCache && cacheKey.isDefined) {
        val key = cacheKey.get
        val cached = queryCache.get(key)
        if (cached != null) {
          val elapsed = System.currentTimeMillis() - startTime
          return SqlResponse(
            success = true,
            result = Some(cached.result),
            executionTimeMs = Some(elapsed)
          )
        }
      }

      Try {
        val result = spark.sql(query)
        val rows = result.collect()
        val output = rows.map(_.toString()).mkString("\n")
        val elapsed = System.currentTimeMillis() - startTime

        if (useCache && cacheKey.isDefined) {
          if (queryCache.size() >= maxCacheSize) {
            queryCache.clear()
          }
          queryCache.put(cacheKey.get, CachedQuery(output, System.currentTimeMillis()))
        }

        SqlResponse(
          success = true,
          result = Some(output),
          rowCount = Some(rows.length.toLong),
          executionTimeMs = Some(elapsed)
        )
      } match {
        case Success(response) => response
        case Failure(ex) =>
          val elapsed = System.currentTimeMillis() - startTime
          SqlResponse(
            success = false,
            error = Some(s"Query execution failed: ${ex.getMessage}"),
            executionTimeMs = Some(elapsed)
          )
      }
    }
  }

  def getTables: List[String] = {
    spark.sql("SHOW TABLES").collect().map(_(1).toString).toList
  }

  def getTableSchema(tableName: String): String = {
    Try {
      spark.sql(s"DESCRIBE TABLE $tableName").collect().map(row =>
        s"${row(0)}: ${row(1)}"
      ).mkString("\n")
    } match {
      case Success(schema) => schema
      case Failure(ex) => s"Error: ${ex.getMessage}"
    }
  }

  val routes = {
    pathPrefix("api") {
      pathPrefix("v1") {
        post {
          path("query") {
            entity(as[SqlRequest]) { req =>
              val response = executeQuery(req.query, req.useCache, req.cacheKey)
              complete(response.map(HttpResponse(StatusCodes.OK, entity = ContentTypes.`application/json`, body = Json.toJson(_).toString())))
            }
          } ~
          path("execute") {
            entity(as[String]) { query =>
              val response = executeQuery(query, useCache = false)
              complete(response.map(HttpResponse(StatusCodes.OK, entity = ContentTypes.`application/json`, body = Json.toJson(_).toString())))
            }
          }
        } ~
        get {
          path("tables") {
            val tableList = getTables
            complete(HttpResponse(StatusCodes.OK, entity = ContentTypes.`application/json`, body = Json.toJson(Map("tables" -> tableList)).toString()))
          } ~
          path("schema" / Segment) { tableName =>
            val schema = getTableSchema(tableName)
            complete(HttpResponse(StatusCodes.OK, entity = ContentTypes.`application/json`, body = Json.toJson(Map("schema" -> schema)).toString()))
          } ~
          path("health") {
            complete(HttpResponse(StatusCodes.OK, entity = ContentTypes.`application/json`, body = Json.toJson(Map("status" -> "healthy")).toString()))
          }
        }
      }
    }
  }

  def main(args: Array[String]): Unit = {
    println("Initializing Spark SQL Analytics API...")
    initializeSampleData()
    println("Sample data loaded successfully")
    println("Available tables: customers, orders, products")

    val host = "127.0.0.1"
    val port = 8080

    val bindingFuture = Http().bindAndHandle(routes, host, port)
    println(s"Server running at http://$host:$port/")
    println("Press ENTER to stop the server")

    scala.io.StdIn.readLine()

    bindingFuture
      .flatMap(_.unbind())
      .onComplete(_ => system.terminate())
  }
}