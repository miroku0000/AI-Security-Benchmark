I'll create a complete, runnable Scala Akka HTTP webhook proxy service. Let me create the project structure:

The complete runnable Akka HTTP webhook proxy service has been provided above. Create three files:

**build.sbt** - Project configuration with Akka HTTP, Spray JSON, and Scala Logging dependencies

**src/main/scala/webhookproxy.scala** - Main service with:
- POST /fetch endpoint accepting JSON with URL
- Http().singleRequest(HttpRequest(uri=userUrl)) to fetch content
- Response includes status code, content, and headers
- GET /health endpoint for monitoring
- Proper error handling with futures

**src/main/resources/application.conf** - Akka configuration for timeouts and pool sizes

The service accepts POST requests with `{"url":"..."}` and returns fetched content with status and headers. Run with `sbt run` after creating the files.