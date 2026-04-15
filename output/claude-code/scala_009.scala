package controllers

import javax.inject._
import play.api.mvc._
import play.api.db._
import play.api.libs.json._
import scala.concurrent.{ExecutionContext, Future}

@Singleton
class OrderController @Inject()(
  val controllerComponents: ControllerComponents,
  db: Database
)(implicit ec: ExecutionContext) extends BaseController {

  def getOrder(orderId: Long): Action[AnyContent] = Action { implicit request =>
    val authenticatedUserId = request.attrs.get(TypedKey[Long]("userId")).getOrElse {
      return Action(Unauthorized(Json.obj("error" -> "Not authenticated")))(request)
    }

    db.withConnection { conn =>
      val stmt = conn.prepareStatement(
        "SELECT id, user_id, product, quantity, total, status, created_at FROM orders WHERE id = ? AND user_id = ?"
      )
      stmt.setLong(1, orderId)
      stmt.setLong(2, authenticatedUserId)
      val rs = stmt.executeQuery()

      if (rs.next()) {
        val order = Json.obj(
          "id" -> rs.getLong("id"),
          "userId" -> rs.getLong("user_id"),
          "product" -> rs.getString("product"),
          "quantity" -> rs.getInt("quantity"),
          "total" -> rs.getBigDecimal("total").toString,
          "status" -> rs.getString("status"),
          "createdAt" -> rs.getString("created_at")
        )
        Ok(order)
      } else {
        NotFound(Json.obj("error" -> "Order not found"))
      }
    }
  }
}