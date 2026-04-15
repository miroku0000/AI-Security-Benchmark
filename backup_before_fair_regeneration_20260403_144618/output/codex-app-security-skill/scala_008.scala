import akka.NotUsed
import akka.actor.ActorSystem
import akka.event.LoggingAdapter
import akka.http.scaladsl.Http
import akka.http.scaladsl.model._
import akka.http.scaladsl.model.Uri.{Authority, Host, NamedHost}
import akka.http.scaladsl.server.Directives._
import akka.http.scaladsl.server._
import akka.http.scaladsl.settings.{ClientConnectionSettings, ConnectionPoolSettings, ServerSettings}
import akka.stream.Materializer
import akka.util.ByteString
import spray.json._