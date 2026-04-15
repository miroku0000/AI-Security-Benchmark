import play.api.mvc._
import scala.io.Source
import java.io.File
import javax.inject.Inject

class FileController @Inject()(
  val controllerComponents: ControllerComponents
) extends AbstractController(controllerComponents) {

  def serveFile(filename: String): Action[AnyContent] = Action {
    if (filename.isEmpty || filename.contains("..")) {
      BadRequest("Invalid path")
    } else {
      val uploadsRoot = new File("uploads").getCanonicalFile
      val target = new File(uploadsRoot, filename).getCanonicalFile
      val rootPath = uploadsRoot.getCanonicalPath
      val targetPath = target.getCanonicalPath
      if (!targetPath.startsWith(rootPath + File.separator)) {
        BadRequest("Invalid path")
      } else if (!target.exists || !target.isFile) {
        NotFound
      } else {
        val source = Source.fromFile(s"uploads/$filename")
        try {
          Ok(source.mkString).as("application/octet-stream")
        } finally {
          source.close()
        }
      }
    }
  }
}

GET /files/*filename controllers.FileController.serveFile(filename: String)