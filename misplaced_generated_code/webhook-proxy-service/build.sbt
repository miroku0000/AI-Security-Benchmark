ThisBuild / scalaVersion := "2.13.14"
ThisBuild / version := "0.1.0"

lazy val akkaVersion = "2.8.5"
lazy val akkaHttpVersion = "10.5.3"

lazy val root = (project in file("."))
  .settings(
    name := "webhook-proxy-service",
    Compile / run / mainClass := Some("com.example.webhook.WebhookProxyApp"),
    libraryDependencies ++= Seq(
      "com.typesafe.akka" %% "akka-http" % akkaHttpVersion,
      "com.typesafe.akka" %% "akka-http-spray-json" % akkaHttpVersion,
      "com.typesafe.akka" %% "akka-stream" % akkaVersion,
      "com.typesafe.akka" %% "akka-actor" % akkaVersion
    ),
    fork := true
  )
