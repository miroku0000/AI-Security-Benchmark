ThisBuild / scalaVersion := "2.13.14"
name := "akka-untrusted-deser"
version := "0.1.0"

libraryDependencies += "com.typesafe.akka" %% "akka-actor" % "2.8.5"

Compile / run / fork := true
