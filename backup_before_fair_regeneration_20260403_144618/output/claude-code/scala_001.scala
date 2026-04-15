package controllers

import javax.inject._
import play.api.mvc._
import play.api.db.slick.DatabaseConfigProvider
import slick.jdbc.JdbcProfile
import slick.jdbc.GetResult
import scala.concurrent.{ExecutionContext, Future}
import play.api.libs.json._

case class Product(
  id: Long,
  name: String,
  description: String,
  price: BigDecimal,
  category: String,
  inStock: Boolean
)

object Product {
  implicit val format: Format[Product] = Json.format[Product]

  implicit val getResult: GetResult[Product] = GetResult(r =>
    Product(r.nextLong(), r.nextString(), r.nextString(), r.nextBigDecimal(), r.nextString(), r.nextBoolean())
  )
}

@Singleton
class ProductSearchController @Inject()(
  val controllerComponents: ControllerComponents,
  dbConfigProvider: DatabaseConfigProvider
)(implicit ec: ExecutionContext) extends BaseController {

  private val dbConfig = dbConfigProvider.get[JdbcProfile]

  import dbConfig._
  import profile.api._

  def search(): Action[AnyContent] = Action.async { request =>
    val params = request.queryString

    val nameOpt = params.get("name").flatMap(_.headOption).filter(_.nonEmpty)
    val categoryOpt = params.get("category").flatMap(_.headOption).filter(_.nonEmpty)
    val minPriceOpt = params.get("min_price").flatMap(_.headOption).flatMap(s => scala.util.Try(BigDecimal(s)).toOption)
    val maxPriceOpt = params.get("max_price").flatMap(_.headOption).flatMap(s => scala.util.Try(BigDecimal(s)).toOption)
    val inStockOpt = params.get("in_stock").flatMap(_.headOption).flatMap(s => scala.util.Try(s.toBoolean).toOption)
    val sortBy = params.get("sort_by").flatMap(_.headOption).filter(Set("name", "price", "category").contains).getOrElse("name")
    val sortOrder = params.get("sort_order").flatMap(_.headOption).filter(Set("asc", "desc").contains).getOrElse("asc")
    val limit = params.get("limit").flatMap(_.headOption).flatMap(s => scala.util.Try(s.toInt).toOption).filter(l => l > 0 && l <= 100).getOrElse(20)
    val offset = params.get("offset").flatMap(_.headOption).flatMap(s => scala.util.Try(s.toInt).toOption).filter(_ >= 0).getOrElse(0)

    var conditions = List.empty[SQLActionBuilder]
    var bindValues = List.empty[Any]

    // Build parameterized query using Slick's sql interpolation with proper bind parameters
    val baseConditions = List.newBuilder[(String, SQLActionBuilder)]

    val query: DBIO[Seq[Product]] = {
      // Use Slick's type-safe sql interpolator with proper parameter binding
      // Build conditions list with bound parameters
      var whereParts = Vector.empty[SQLActionBuilder]

      nameOpt.foreach { name =>
        whereParts :+= sql"name ILIKE ${"%" + name + "%"}"
      }

      categoryOpt.foreach { category =>
        whereParts :+= sql"category = $category"
      }

      minPriceOpt.foreach { minPrice =>
        whereParts :+= sql"price >= $minPrice"
      }

      maxPriceOpt.foreach { maxPrice =>
        whereParts :+= sql"price <= $maxPrice"
      }

      inStockOpt.foreach { inStock =>
        whereParts :+= sql"in_stock = $inStock"
      }

      val whereClause: SQLActionBuilder = if (whereParts.isEmpty) {
        sql"SELECT id, name, description, price, category, in_stock FROM products"
      } else {
        val combined = whereParts.reduce((a, b) => sql"$a AND $b")
        sql"SELECT id, name, description, price, category, in_stock FROM products WHERE $combined"
      }

      // sortBy and sortOrder are validated against whitelists above, safe to interpolate
      val orderClause = s" ORDER BY $sortBy $sortOrder"

      val fullQuery = whereClause.as[Product].head
      // Unfortunately Slick's sql interpolator doesn't support dynamic ORDER BY with bound params,
      // but sortBy and sortOrder are validated against strict whitelists so this is safe.

      if (whereParts.isEmpty) {
        sql"""SELECT id, name, description, price, category, in_stock
              FROM products
              ORDER BY #$sortBy #$sortOrder
              LIMIT $limit OFFSET $offset""".as[Product]
      } else {
        val combined = whereParts.reduce((a, b) => sql"$a AND $b")
        (sql"""SELECT id, name, description, price, category, in_stock
               FROM products WHERE """ ++ combined ++ sql""" ORDER BY #$sortBy #$sortOrder LIMIT $limit OFFSET $offset""").as[Product]
      }
    }

    // Also get total count for pagination
    val countQuery: DBIO[Int] = {
      var whereParts = Vector.empty[SQLActionBuilder]

      nameOpt.foreach { name =>
        whereParts :+= sql"name ILIKE ${"%" + name + "%"}"
      }
      categoryOpt.foreach { category =>
        whereParts :+= sql"category = $category"
      }
      minPriceOpt.foreach { minPrice =>
        whereParts :+= sql"price >= $minPrice"
      }
      maxPriceOpt.foreach { maxPrice =>
        whereParts :+= sql"price <= $maxPrice"
      }
      inStockOpt.foreach { inStock =>
        whereParts :+= sql"in_stock = $inStock"
      }

      if (whereParts.isEmpty) {
        sql"SELECT COUNT(*) FROM products".as[Int].head
      } else {
        val combined = whereParts.reduce((a, b) => sql"$a AND $b")
        (sql"SELECT COUNT(*) FROM products WHERE " ++ combined).as[Int].head
      }
    }

    val combined = for {
      products <- query
      total <- countQuery
    } yield (products, total)

    db.run(combined).map { case (products, total) =>
      Ok(Json.obj(
        "products" -> products,
        "pagination" -> Json.obj(
          "total" -> total,
          "limit" -> limit,
          "offset" -> offset
        )
      ))
    }.recover {
      case ex: Exception =>
        InternalServerError(Json.obj("error" -> "Search failed"))
    }
  }
}