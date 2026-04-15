ThisBuild / scalaVersion := "2.13.14"
ThisBuild / version := "0.1.0"

lazy val awsSdk = "2.25.27"

lazy val root = (project in file("."))
  .settings(
    name := "aws-scala-service",
    Compile / run / mainClass := Some("com.example.aws.AwsServiceApp"),
    libraryDependencies ++= Seq(
      "software.amazon.awssdk" % "auth" % awsSdk,
      "software.amazon.awssdk" % "regions" % awsSdk,
      "software.amazon.awssdk" % "sts" % awsSdk,
      "software.amazon.awssdk" % "s3" % awsSdk
    ),
    fork := true
  )
