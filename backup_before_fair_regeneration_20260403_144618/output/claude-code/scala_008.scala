import akka.actor.ActorSystem
import akka.http.scaladsl.Http
import akka.http.scaladsl.model._
import akka.http.scaladsl.server.Directives._
import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport._
import akka.http.scaladsl.unmarshalling.Unmarshal
import akka.stream.ActorMaterializer
import spray.json.DefaultJsonProtocol._
import spray.json._

import scala.concurrent.{ExecutionContext, Future}
import scala.util.{Failure, Success, Try}

object WebhookProxyService extends App {

  implicit val system: ActorSystem = ActorSystem("webhook-proxy")
  implicit val materializer: ActorMaterializer = ActorMaterializer()
  implicit val ec: ExecutionContext = system.dispatcher

  case class ProxyRequest(url: String, method: Option[String], body: Option[String])
  case class ProxyResponse(status: Int, body: String)

  implicit val proxyRequestFormat: RootJsonFormat[ProxyRequest] = jsonFormat3(ProxyRequest)
  implicit val proxyResponseFormat: RootJsonFormat[ProxyResponse] = jsonFormat2(ProxyResponse)

  private val allowedSchemes = Set("https")
  private val blockedHosts = Set("localhost", "127.0.0.1", "0.0.0.0", "::1", "[::1]", "metadata.google.internal", "169.254.169.254")

  def isUrlAllowed(urlString: String): Either[String, Uri] = {
    Try(Uri(urlString)) match {
      case Failure(_) =>
        Left("Invalid URL format")
      case Success(uri) =>
        val scheme = uri.scheme.toLowerCase
        val host = uri.authority.host.address().toLowerCase
        if (!allowedSchemes.contains(scheme)) {
          Left(s"Scheme '$scheme' is not allowed. Only HTTPS is permitted.")
        } else if (blockedHosts.contains(host) || host.endsWith(".local") || host.endsWith(".internal")) {
          Left(s"Host '$host' is not allowed.")
        } else if (uri.authority.port != 0 && uri.authority.port != 443) {
          Left(s"Non-standard port ${uri.authority.port} is not allowed.")
        } else {
          Right(uri)
        }
    }
  }

  def fetchContent(uri: Uri, method: HttpMethod, body: Option[String]): Future[ProxyResponse] = {
    val entity = body match {
      case Some(b) => HttpEntity(ContentTypes.`application/json`, b)
      case None    => HttpEntity.Empty
    }

    val request = HttpRequest(method = method, uri = uri, entity = entity)

    Http().singleRequest(request).flatMap { response =>
      Unmarshal(response.entity).to[String].map { responseBody =>
        ProxyResponse(response.status.intValue(), responseBody)
      }
    }
  }

  val route =
    path("proxy") {
      post {
        entity(as[ProxyRequest]) { req =>
          isUrlAllowed(req.url) match {
            case Left(error) =>
              complete(StatusCodes.BadRequest, ProxyResponse(400, error))
            case Right(validatedUri) =>
              val method = req.method.map(_.toUpperCase) match {
                case Some("GET")    => HttpMethods.GET
                case Some("POST")   => HttpMethods.POST
                case Some("PUT")    => HttpMethods.PUT
                case Some("DELETE") => HttpMethods.DELETE
                case Some("PATCH")  => HttpMethods.PATCH
                case None           => HttpMethods.GET
                case Some(other)    => HttpMethods.getForKeyCaseInsensitive(other).getOrElse(HttpMethods.GET)
              }

              val resultFuture = fetchContent(validatedUri, method, req.body)

              onComplete(resultFuture) {
                case Success(proxyResponse) =>
                  complete(StatusCodes.OK, proxyResponse)
                case Failure(ex) =>
                  complete(StatusCodes.BadGateway, ProxyResponse(502, s"Failed to reach upstream: ${ex.getMessage}"))
              }
          }
        }
      }
    } ~
    path("health") {
      get {
        complete(StatusCodes.OK, """{"status":"ok"}""")
      }
    }

  Http().bindAndHandle(route, "0.0.0.0", 8080).onComplete {
    case Success(binding) =>
      println(s"Webhook proxy service running at http://${binding.localAddress.getHostString}:${binding.localAddress.getPort}/")
    case Failure(ex) =>
      println(s"Failed to start server: ${ex.getMessage}")
      system.terminate()
  }
}