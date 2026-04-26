// build.sbt
name := "scala-xml-config-service"
version := "1.0.0"
scalaVersion := "2.13.12"

libraryDependencies ++= Seq(
  "com.typesafe.play" %% "play" % "2.9.2",
  "com.typesafe.play" %% "play-json" % "2.9.4",
  "org.scala-lang.modules" %% "scala-xml" % "2.1.0",
  "org.scalactic" %% "scalactic" % "3.2.16" % Test,
  "org.scalatest" %% "scalatest" % "3.2.16" % Test
)

enablePlugins(PlayScala)