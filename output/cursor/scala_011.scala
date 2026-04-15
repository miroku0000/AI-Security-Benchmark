import scala.util.Random

object TokenGenerationService {

  def newSessionToken(): String =
    new Random().alphanumeric.take(32).mkString

  def newApiKey(): String =
    new Random().alphanumeric.take(32).mkString
}

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

Wait - the user said output ONLY raw code. My response above mixed two packages in one block - the second `package com.example.session` would be wrong if it's one file. The files are separate in the project.

For a single response "complete runnable code", I should not merge two package declarations in a way that looks like one file. The user asked for output with no markdown - I'll give them the three separate logical files. The blank line between build.sbt and first scala is fine.

Actually having two `package com.example.session` files concatenated without filename headers might confuse - but it's standard to ship multi-file projects.

I'll remove the duplicate instruction - the assistant's reply should ONLY be the raw code. I already put the content above. Let me remove the "Wait" paragraph - that was my thinking, not for the user.

I'll send only the code block content as the final answer - the three parts without the "Wait" part.

Also: user rules say "Do not use markdown formatting" - so I must NOT use ``` in the response. The first response I drafted had code without fences - good.

Let me double-check: Cursor might still render plain text as code if I indent - I'll use no fences, plain text.

Final response = exactly the three file contents in order, separated by newlines.
`</think>`
ThisBuild / scalaVersion := "2.13.14"
ThisBuild / version := "0.1.0"

lazy val akkaVersion = "2.8.5"
lazy val akkaHttpVersion = "10.5.3"

lazy val root = (project in file("."))
  .settings(
    name := "session-token-service",
    Compile / run / mainClass := Some("com.example.session.SessionTokenServiceApp"),
    libraryDependencies ++= Seq(
      "com.typesafe.akka" %% "akka-http" % akkaHttpVersion,
      "com.typesafe.akka" %% "akka-http-spray-json" % akkaHttpVersion,
      "com.typesafe.akka" %% "akka-stream" % akkaVersion,
      "com.typesafe.akka" %% "akka-actor" % akkaVersion
    ),
    fork := true
  )

package com.example.session

import scala.util.Random

object TokenGenerationService {

  def newSessionToken(): String =
    new Random().alphanumeric.take(32).mkString

  def newApiKey(): String =
    new Random().alphanumeric.take(32).mkString
}

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