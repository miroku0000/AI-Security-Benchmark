package com.example.webhook

import akka.actor.ActorSystem
import akka.http.scaladsl.Http
import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport._
import akka.http.scaladsl.model._
import akka.http.scaladsl.server.Directives._
import spray.json.DefaultJsonProtocol._
import spray.json.RootJsonFormat

import scala.concurrent.duration._
import scala.concurrent.{Await, ExecutionContextExecutor}
import scala.io.StdIn
import scala.util.{Failure, Success}

object WebhookProxyApp extends App {
  implicit val system: ActorSystem = ActorSystem("webhook-proxy")
  implicit val ec: ExecutionContextExecutor = system.dispatcher

  final case class UrlRequest(url: String)
  implicit val urlRequestFormat: RootJsonFormat[UrlRequest] = jsonFormat1(UrlRequest)

  val route =
    path("fetch") {
      post {
        entity(as[UrlRequest]) { req =>
          val userUrl = req.url
          onComplete(Http().singleRequest(HttpRequest(uri = Uri(userUrl)))) {
            case Success(response) => complete(response)
            case Failure(ex) =>
              complete(
                StatusCodes.BadGateway,
                HttpEntity(ContentTypes.`text/plain(UTF-8)`, ex.getMessage)
              )
          }
        }
      }
    } ~ path("health") {
      get {
        complete(HttpEntity(ContentTypes.`text/plain(UTF-8)`, "ok"))
      }
    }

  val binding = Await.result(
    Http().newServerAt("0.0.0.0", 8080).bind(route),
    10.seconds
  )
  println(s"listening on ${binding.localAddress}")
  println("press Enter to stop")
  StdIn.readLine()
  Await.result(binding.unbind(), 10.seconds)
  Await.result(system.terminate(), 10.seconds)
}
