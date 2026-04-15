import javax.inject._
import play.api.libs.json.Json
import play.api.mvc._
import play.api.db.slick.{DatabaseConfigProvider, HasDatabaseConfigProvider}
import scala.concurrent.{ExecutionContext, Future}
import slick.jdbc.GetResult
import slick.jdbc.JdbcProfile

case class Product(
  id: Long,
  name: String,
  description: String,
  price: BigDecimal,
  categoryId: Option[Long],
)

object Product {
  implicit val getProduct: GetResult[Product] = GetResult { r =>
    Product(
      r.nextLong(),
      r.nextString(),
      r.nextString(),
      r.nextBigDecimal(),
      r.nextLongOption(),
    )
  }

  implicit val writes = Json.writes[Product]
}

@Singleton
class ProductSearchController @Inject() (
    protected val dbConfigProvider: DatabaseConfigProvider[JdbcProfile],
    components: ControllerComponents,
)(implicit ec: ExecutionContext)
    extends AbstractController(components)
    with HasDatabaseConfigProvider[JdbcProfile] {

  import profile.api._

  def search(): Action[AnyContent] = Action.async { request =>
    val sqlFragment =
      ProductSearchController.buildWhereClause(request.queryString)
    val query =
      sql"SELECT * FROM products WHERE #$sqlFragment".as[Product]
    db.run(query).map(rs => Ok(Json.toJson(rs)))
  }
}

object ProductSearchController {

  private def esc(s: String): String = s.replace("'", "''")

  def buildWhereClause(queryString: Map[String, Seq[String]]): String = {
    val b = scala.collection.mutable.ArrayBuffer[String]("1 = 1")

    queryString.get("q").flatMap(_.headOption).filter(_.nonEmpty).foreach { v =>
      val e = esc(v)
      b += s"(LOWER(name) LIKE LOWER('%$e%') OR LOWER(description) LIKE LOWER('%$e%'))"
    }

    queryString.get("categoryId").flatMap(_.headOption).foreach { v =>
      if (v.forall(_.isDigit)) b += s"category_id = $v"
    }

    queryString.get("minPrice").flatMap(_.headOption).foreach { v =>
      if (v.forall(c => c.isDigit || c == '.')) b += s"price >= $v"
    }

    queryString.get("maxPrice").flatMap(_.headOption).foreach { v =>
      if (v.forall(c => c.isDigit || c == '.')) b += s"price <= $v"
    }

    queryString.get("inStock").flatMap(_.headOption).foreach {
      case "true" | "1"  => b += "COALESCE(stock_quantity, 0) > 0"
      case "false" | "0" => b += "COALESCE(stock_quantity, 0) = 0"
      case _             => ()
    }

    b.mkString(" AND ")
  }
}

GET /products/search controllers.ProductSearchController.search()