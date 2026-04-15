object Main {
  def main(args: Array[String]): Unit = {
    val exitCode =
      try {
        val config = AppConfig.load()
        val service = new AwsService(config)
        try {
          println(service.callerIdentity())
          service.listBucketNames().foreach(name => println(s"bucket=$name"))
          0
        } finally {
          service.close()
        }
      } catch {
        case e: IllegalArgumentException =>
          Console.err.println(s"Configuration error: ${e.getMessage}")
          2
        case e: StsException =>
          Console.err.println(s"AWS authentication failed: ${sanitizeAwsMessage(e.getMessage)}")
          3
        case NonFatal(e) =>
          Console.err.println(s"AWS operation failed: ${sanitizeAwsMessage(e.getMessage)}")
          4
      }