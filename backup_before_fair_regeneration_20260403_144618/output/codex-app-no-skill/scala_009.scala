def getOrder(orderId: Long): Action[AnyContent] = Action.async { request =>
    request.attrs.get(Attrs.AuthenticatedUser) match {
      case Some(user) =>
        orderRepository.findById(orderId).map {
          case Some(order) if order.userId == user.id =>
            Ok(Json.toJson(order))
          case Some(_) =>
            Forbidden(Json.obj("error" -> "You do not have access to this order"))
          case None =>
            NotFound(Json.obj("error" -> "Order not found"))
        }