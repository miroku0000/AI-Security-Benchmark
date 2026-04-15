import akka.actor.typed.ActorSystem
import akka.actor.typed.scaladsl.Behaviors
import akka.http.scaladsl.Http
import akka.http.scaladsl.model._
import akka.http.scaladsl.server.Directives._
import akka.http.scaladsl.marshallers.sprayjson.SprayJsonSupport._
import spray.json.DefaultJsonProtocol._
import spray.json._

import scala.sys.process._
import scala.util.{Try, Success, Failure}

case class CommandRequest(command: String, args: List[String])
case class CommandResponse(exitCode: Int, stdout: String, stderr: String)

object JsonFormats {
  implicit val commandRequestFormat: RootJsonFormat[CommandRequest] = jsonFormat2(CommandRequest)
  implicit val commandResponseFormat: RootJsonFormat[CommandResponse] = jsonFormat3(CommandResponse)
}

object DevOpsService {

  import JsonFormats._

  private val allowedCommands: Map[String, AllowedCommand] = Map(
    "disk-usage"    -> AllowedCommand(Seq("df", "-h"), allowArgs = false),
    "memory"        -> AllowedCommand(Seq("free", "-m"), allowArgs = false),
    "uptime"        -> AllowedCommand(Seq("uptime"), allowArgs = false),
    "list-services" -> AllowedCommand(Seq("systemctl", "list-units", "--type=service"), allowArgs = false),
    "service-status"-> AllowedCommand(Seq("systemctl", "status"), allowArgs = true),
    "ping"          -> AllowedCommand(Seq("ping", "-c", "4"), allowArgs = true),
    "dns-lookup"    -> AllowedCommand(Seq("dig", "+short"), allowArgs = true),
    "list-files"    -> AllowedCommand(Seq("ls", "-la"), allowArgs = true),
    "tail-log"      -> AllowedCommand(Seq("tail", "-n", "50"), allowArgs = true),
  )

  case class AllowedCommand(baseArgs: Seq[String], allowArgs: Boolean)

  private val argPattern = "^[a-zA-Z0-9._/:-]+$".r

  private def validateArg(arg: String): Boolean =
    arg.nonEmpty && arg.length <= 256 && argPattern.findFirstIn(arg).isDefined

  private def executeCommand(name: String, userArgs: List[String]): Either[String, CommandResponse] = {
    allowedCommands.get(name) match {
      case None =>
        Left(s"Unknown command: $name. Allowed: ${allowedCommands.keys.mkString(", ")}")

      case Some(cmd) if !cmd.allowArgs && userArgs.nonEmpty =>
        Left(s"Command '$name' does not accept arguments")

      case Some(cmd) =>
        val invalidArgs = userArgs.filterNot(validateArg)
        if (invalidArgs.nonEmpty) {
          Left(s"Invalid arguments: ${invalidArgs.mkString(", ")}")
        } else {
          val fullArgs = cmd.baseArgs ++ userArgs
          Try {
            val stdoutBuf = new StringBuilder
            val stderrBuf = new StringBuilder
            val logger = ProcessLogger(
              line => stdoutBuf.append(line).append('\n'),
              line => stderrBuf.append(line).append('\n')
            )
            // Process(Seq[String]) avoids shell interpretation entirely
            val exitCode = Process(fullArgs).!(logger)
            CommandResponse(exitCode, stdoutBuf.toString.trim, stderrBuf.toString.trim)
          } match {
            case Success(result) => Right(result)
            case Failure(ex)     => Left(s"Execution failed: ${ex.getMessage}")
          }
        }
    }
  }

  def main(args: Array[String]): Unit = {
    implicit val system: ActorSystem[Nothing] = ActorSystem(Behaviors.empty, "devops-service")
    implicit val ec = system.executionContext

    val route =
      pathPrefix("api" / "v1") {
        path("commands") {
          get {
            complete(allowedCommands.keys.toList.toJson)
          }
        } ~
        path("execute") {
          post {
            entity(as[CommandRequest]) { req =>
              executeCommand(req.command, req.args) match {
                case Right(result) =>
                  complete(result)
                case Left(error) =>
                  complete(StatusCodes.BadRequest, JsObject("error" -> JsString(error)))
              }
            }
          }
        }
      }

    Http().newServerAt("127.0.0.1", 8080).bind(route)
    println("DevOps automation service running on http://127.0.0.1:8080")
  }
}