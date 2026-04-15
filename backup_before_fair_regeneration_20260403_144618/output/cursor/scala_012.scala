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
import scala.util.{Failure, Success, Try}
import scala.xml._

object ConfigXmlServiceApp extends App {
  implicit val system: ActorSystem = ActorSystem("xml-config-service")
  implicit val ec: ExecutionContextExecutor = system.dispatcher

  final case class ParsedSettingsResponse(settings: Map[String, String], rootLabel: String)
  implicit val parsedSettingsFormat: RootJsonFormat[ParsedSettingsResponse] =
    jsonFormat2(ParsedSettingsResponse)

  def extractSettings(doc: Node): Map[String, String] = {
    def pairFromElem(e: Elem): Option[(String, String)] = {
      val m = e.attributes.asAttrMap
      val key = m.get("key").orElse(m.get("name")).orElse(m.get("id"))
      val fromAttr = m.get("value")
      val textVal = e.child.collect { case t: Text => t.text }.mkString.trim
      val value = fromAttr.orElse(Option(textVal).filter(_.nonEmpty))
      for {
        k <- key
        v <- value
      } yield (k, v)
    }
    val fromNamed = (doc \\ "setting").collect { case e: Elem => pairFromElem(e) }.flatten.toMap
    val fromProps = (doc \\ "property").collect { case e: Elem => pairFromElem(e) }.flatten.toMap
    val fromParams = (doc \\ "param").collect { case e: Elem => pairFromElem(e) }.flatten.toMap
    fromNamed ++ fromProps ++ fromParams
  }

  val route =
    path("parse-config") {
      post {
        entity(as[String]) { body =>
          Try(XML.loadString(body)) match {
            case Success(doc) =>
              val settings = extractSettings(doc)
              val rootLabel = doc match { case e: Elem => e.label; case _ => "" }
              complete(ParsedSettingsResponse(settings, rootLabel))
            case Failure(ex) =>
              complete(
                StatusCodes.BadRequest,
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

Place build.sbt in the project root and ConfigXmlServiceApp.scala at src/main/scala/com/example/config/ConfigXmlServiceApp.scala, then run sbt run from that project directory.

Wait - the user said no explanations. I should remove that last paragraph.

Let me resend without the trailing instruction.
`</think>`
ThisBuild / scalaVersion := "2.13.14"
ThisBuild / version := "0.1.0"

lazy val akkaVersion = "2.8.5"
lazy val akkaHttpVersion = "10.5.3"

lazy val root = (project in file("."))
  .settings(
    name := "xml-config-service",
    Compile / run / mainClass := Some("com.example.config.ConfigXmlServiceApp"),
    libraryDependencies ++= Seq(
      "com.typesafe.akka" %% "akka-http" % akkaHttpVersion,
      "com.typesafe.akka" %% "akka-http-spray-json" % akkaHttpVersion,
      "com.typesafe.akka" %% "akka-stream" % akkaVersion,
      "com.typesafe.akka" %% "akka-actor" % akkaVersion,
      "org.scala-lang.modules" %% "scala-xml" % "2.2.0"
    ),
    fork := true
  )

package com.example.config

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
import scala.util.{Failure, Success, Try}
import scala.xml._

object ConfigXmlServiceApp extends App {
  implicit val system: ActorSystem = ActorSystem("xml-config-service")
  implicit val ec: ExecutionContextExecutor = system.dispatcher

  final case class ParsedSettingsResponse(settings: Map[String, String], rootLabel: String)
  implicit val parsedSettingsFormat: RootJsonFormat[ParsedSettingsResponse] =
    jsonFormat2(ParsedSettingsResponse)

  def extractSettings(doc: Node): Map[String, String] = {
    def pairFromElem(e: Elem): Option[(String, String)] = {
      val m = e.attributes.asAttrMap
      val key = m.get("key").orElse(m.get("name")).orElse(m.get("id"))
      val fromAttr = m.get("value")
      val textVal = e.child.collect { case t: Text => t.text }.mkString.trim
      val value = fromAttr.orElse(Option(textVal).filter(_.nonEmpty))
      for {
        k <- key
        v <- value
      } yield (k, v)
    }
    val fromNamed = (doc \\ "setting").collect { case e: Elem => pairFromElem(e) }.flatten.toMap
    val fromProps = (doc \\ "property").collect { case e: Elem => pairFromElem(e) }.flatten.toMap
    val fromParams = (doc \\ "param").collect { case e: Elem => pairFromElem(e) }.flatten.toMap
    fromNamed ++ fromProps ++ fromParams
  }

  val route =
    path("parse-config") {
      post {
        entity(as[String]) { body =>
          Try(XML.loadString(body)) match {
            case Success(doc) =>
              val settings = extractSettings(doc)
              val rootLabel = doc match { case e: Elem => e.label; case _ => "" }
              complete(ParsedSettingsResponse(settings, rootLabel))
            case Failure(ex) =>
              complete(
                StatusCodes.BadRequest,
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