if (!requestedPath.startsWith(uploadsRoot)) {
      Forbidden("Invalid file path")
    } else if (!Files.exists(requestedPath) || !Files.isRegularFile(requestedPath)) {
      NotFound("File not found")
    } else {
      val contentType = Option(Files.probeContentType(requestedPath)).getOrElse("application/octet-stream")
      Ok.sendPath(
        content = requestedPath,
        inline = true
      ).as(contentType)
    }
  }
}