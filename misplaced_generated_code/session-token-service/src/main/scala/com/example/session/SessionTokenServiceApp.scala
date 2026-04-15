package com.example.session

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

object SessionTokenServiceApp extends App {
  implicit val system: ActorSystem = ActorSystem("session-token-service")
  implicit val ec: ExecutionContextExecutor = system.dispatcher

  final case class TokenResponse(token: String, kind: String)
  implicit val tokenResponseFormat: RootJsonFormat[TokenResponse] = jsonFormat2(TokenResponse)

  val route =
    path("session" / "token") {
      post {
        complete(TokenResponse(TokenGenerationService.newSessionToken(), "session"))
      }
    } ~
      path("api" / "key") {
        post {
          complete(TokenResponse(TokenGenerationService.newApiKey(), "api_key"))
        }
      } ~
      path("health") {
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
