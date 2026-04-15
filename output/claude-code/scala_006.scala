package controllers

import javax.inject._
import play.api.mvc._
import scala.io.Source
import scala.util.{Try, Using}
import java.nio.file.{Path, Paths}

@Singleton
class FileController @Inject()(val controllerComponents: ControllerComponents) extends BaseController {

  private val uploadsDir = Paths.get("uploads").toAbsolutePath.normalize

  def serveFile(filename: String): Action[AnyContent] = Action {
    val requestedPath: Path = uploadsDir.resolve(filename).normalize

    if (!requestedPath.startsWith(uploadsDir)) {
      Forbidden("Access denied: path traversal detected")
    } else if (!requestedPath.toFile.exists()) {
      NotFound("File not found")
    } else if (!requestedPath.toFile.isFile) {
      BadRequest("Not a file")
    } else {
      Using(Source.fromFile(requestedPath.toFile, "UTF-8")) { source =>
        Ok(source.mkString)
      }.getOrElse(InternalServerError("Could not read file"))
    }
  }
}