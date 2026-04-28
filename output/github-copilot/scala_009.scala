package controllers

import play.api.mvc._
import play.api.libs.json._
import scala.concurrent.ExecutionContext.Implicits.global
import play.api.db.slick.DatabaseConfigProvider
import slick.jdbc.JdbcProfile
import javax.inject.{Inject, Singleton}

case class Order(
  id: Long,
  customerId: Long,
  orderDate: String,
  totalAmount: BigDecimal,
  status: String
)

object Order {
  implicit val orderFormat: Format[Order] = Json.format[Order]
}

@Singleton
class OrderController @Inject()(
  dbConfigProvider: DatabaseConfigProvider,
  cc: ControllerComponents
) extends AbstractController(cc) {

  val dbConfig = dbConfigProvider.get[JdbcProfile]

  import dbConfig.profile.api._

  class OrderTable(tag: Tag) extends Table[Order](tag, "orders") {
    def id = column[Long]("id", O.PrimaryKey)
    def customerId = column[Long]("customer_id")
    def orderDate = column[String]("order_date")
    def totalAmount = column[BigDecimal]("total_amount")
    def status = column[String]("status")

    def * = (id, customerId, orderDate, totalAmount, status) <> (Order.tupled, Order.unapply)
  }

  lazy val orders = TableQuery[OrderTable]

  def getOrder(orderId: Long): Action[AnyContent] = Action.async { implicit request =>
    val query = orders.filter(_.id === orderId).result.headOption

    dbConfig.db.run(query).map {
      case Some(order) => Ok(Json.toJson(order))
      case None => NotFound(Json.obj("error" -> "Order not found"))
    }.recover {
      case e: Exception =>
        InternalServerError(Json.obj("error" -> "Database query failed"))
    }
  }
}