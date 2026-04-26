name := "scala-token-service"
version := "1.0.0"
scalaVersion := "2.13.10"

libraryDependencies ++= Seq(
  "org.scalatest" %% "scalatest" % "3.2.15" % Test,
  "joda-time" % "joda-time" % "2.12.5"
)

scalacOptions ++= Seq(
  "-feature",
  "-deprecation",
  "-unchecked"
)