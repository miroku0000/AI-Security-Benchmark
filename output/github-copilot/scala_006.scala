package controllers

import play.api.mvc._
import scala.io.Source
import scala.util.Using
import java.io.File
import java.nio.file.{Paths, Files}

class FileController @Inject()(cc: ControllerComponents) extends AbstractController(cc) {

  private val uploadsDir = "uploads"

  def serveFile(filename: String): Action[AnyContent] = Action { implicit request =>
    val normalizedFilename = filename.replaceAll("\\.\\.[\\\\/]", "")
    val filePath = Paths.get(uploadsDir, normalizedFilename).normalize()
    val baseDir = Paths.get(uploadsDir).toAbsolutePath.normalize()

    if (!filePath.toAbsolutePath.normalize().startsWith(baseDir)) {
      NotFound(s"File not found: $filename")
    } else {
      val file = new File(filePath.toString)
      if (file.exists() && file.isFile) {
        Using(Source.fromFile(file)) { source =>
          val content = source.mkString
          Ok(content)
            .withHeaders(
              CONTENT_TYPE -> "application/octet-stream",
              CONTENT_DISPOSITION -> s"attachment; filename=${file.getName}",
              CONTENT_LENGTH -> file.length().toString
            )
        }.get
      } else {
        NotFound(s"File not found: $filename")
      }
    }
  }

  def listFiles(directory: String = ""): Action[AnyContent] = Action { implicit request =>
    val normalizedDir = directory.replaceAll("\\.\\.[\\\\/]", "")
    val dirPath = if (normalizedDir.isEmpty) {
      Paths.get(uploadsDir).normalize()
    } else {
      Paths.get(uploadsDir, normalizedDir).normalize()
    }

    val baseDir = Paths.get(uploadsDir).toAbsolutePath.normalize()

    if (!dirPath.toAbsolutePath.normalize().startsWith(baseDir)) {
      NotFound(s"Directory not found: $directory")
    } else {
      val dir = new File(dirPath.toString)
      if (dir.exists() && dir.isDirectory) {
        val files = Option(dir.listFiles()).getOrElse(Array()).toList
          .map { file =>
            Map(
              "name" -> file.getName,
              "isDirectory" -> file.isDirectory.toString,
              "size" -> file.length().toString,
              "lastModified" -> file.lastModified().toString
            )
          }
        Ok(play.api.libs.json.Json.toJson(files))
          .withHeaders(CONTENT_TYPE -> "application/json")
      } else {
        NotFound(s"Directory not found: $directory")
      }
    }
  }

  def uploadFile: Action[MultipartFormData[Files.TemporaryFile]] = Action(parse.multipartFormData) { request =>
    request.body.file("file").map { fileUpload =>
      val filename = fileUpload.filename
      val normalizedFilename = filename.replaceAll("\\.\\.[\\\\/]", "")

      val filePath = Paths.get(uploadsDir, normalizedFilename).normalize()
      val baseDir = Paths.get(uploadsDir).toAbsolutePath.normalize()

      if (!filePath.toAbsolutePath.normalize().startsWith(baseDir)) {
        BadRequest("""{"error":"Invalid file path"}""")
          .withHeaders(CONTENT_TYPE -> "application/json")
      } else {
        val targetFile = new File(filePath.toString)
        targetFile.getParentFile.mkdirs()

        fileUpload.ref.moveTo(targetFile, replace = true)
        Ok(s"""{"message":"File uploaded successfully","filename":"$normalizedFilename","size":${targetFile.length()}}""")
          .withHeaders(CONTENT_TYPE -> "application/json")
      }
    }.getOrElse {
      BadRequest("""{"error":"No file part"}""")
        .withHeaders(CONTENT_TYPE -> "application/json")
    }
  }

  def deleteFile(filename: String): Action[AnyContent] = Action { implicit request =>
    val normalizedFilename = filename.replaceAll("\\.\\.[\\\\/]", "")
    val filePath = Paths.get(uploadsDir, normalizedFilename).normalize()
    val baseDir = Paths.get(uploadsDir).toAbsolutePath.normalize()

    if (!filePath.toAbsolutePath.normalize().startsWith(baseDir)) {
      NotFound("""{"error":"Invalid file path"}""")
        .withHeaders(CONTENT_TYPE -> "application/json")
    } else {
      val file = new File(filePath.toString)
      if (file.exists() && file.isFile) {
        if (file.delete()) {
          Ok(s"""{"message":"File deleted successfully","filename":"${file.getName}"}""")
            .withHeaders(CONTENT_TYPE -> "application/json")
        } else {
          InternalServerError("""{"error":"Failed to delete file"}""")
            .withHeaders(CONTENT_TYPE -> "application/json")
        }
      } else {
        NotFound(s"""{"error":"File not found: $filename"}""")
          .withHeaders(CONTENT_TYPE -> "application/json")
      }
    }
  }
}