import java.net.URI
import java.util.concurrent.atomic.AtomicReference

import software.amazon.awssdk.auth.credentials.{
  AwsBasicCredentials,
  AwsCredentialsProvider,
  AwsSessionCredentials,
  DefaultCredentialsProvider,
  ProfileCredentialsProvider,
  StaticCredentialsProvider
}
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3.model.ListBucketsRequest
import software.amazon.awssdk.services.sts.StsClient
import software.amazon.awssdk.services.sts.model.GetCallerIdentityRequest

final case class AwsServiceConfig(
    region: Region,
    profileName: Option[String] = None,
    accessKeyId: Option[String] = None,
    secretAccessKey: Option[String] = None,
    sessionToken: Option[String] = None,
    endpointOverride: Option[URI] = None
)

object AwsCredentialManager {

  def buildProvider(config: AwsServiceConfig): AwsCredentialsProvider = {
    (config.accessKeyId, config.secretAccessKey) match {
      case (Some(ak), Some(sk)) =>
        val creds = config.sessionToken match {
          case Some(st) => AwsSessionCredentials.create(ak, sk, st)
          case None     => AwsBasicCredentials.create(ak, sk)
        }
        StaticCredentialsProvider.create(creds)
      case (None, None) =>
        config.profileName match {
          case Some(p) => ProfileCredentialsProvider.builder().profileName(p).build()
          case None    => DefaultCredentialsProvider.create()
        }
      case _ =>
        throw new IllegalArgumentException(
          "Both accessKeyId and secretAccessKey must be set for static credentials."
        )
    }
  }
}

final class AwsService private (
    val config: AwsServiceConfig,
    credentialsProvider: AwsCredentialsProvider
) extends AutoCloseable {

  private val credRef = new AtomicReference[AwsCredentialsProvider](credentialsProvider)

  def currentCredentialsProvider: AwsCredentialsProvider = credRef.get()

  def refreshCredentials(newProvider: AwsCredentialsProvider): Unit = {
    val old = credRef.getAndSet(newProvider)
    old.close()
  }

  def updateStaticCredentials(
      accessKeyId: String,
      secretAccessKey: String,
      sessionToken: Option[String] = None
  ): Unit = {
    val creds = sessionToken match {
      case Some(st) => AwsSessionCredentials.create(accessKeyId, secretAccessKey, st)
      case None     => AwsBasicCredentials.create(accessKeyId, secretAccessKey)
    }
    refreshCredentials(StaticCredentialsProvider.create(creds))
  }

  def useDefaultCredentialChain(): Unit = {
    refreshCredentials(DefaultCredentialsProvider.create())
  }

  def useProfile(profileName: String): Unit = {
    refreshCredentials(ProfileCredentialsProvider.builder().profileName(profileName).build())
  }

  private def buildStsClient(): StsClient = {
    val b = StsClient.builder().region(config.region).credentialsProvider(credRef.get())
    config.endpointOverride match {
      case Some(uri) => b.endpointOverride(uri).build()
      case None      => b.build()
    }
  }

  private def buildS3Client(): S3Client = {
    val b = S3Client.builder().region(config.region).credentialsProvider(credRef.get())
    config.endpointOverride match {
      case Some(uri) => b.endpointOverride(uri).build()
      case None      => b.build()
    }
  }

  def withStsClient[A](f: StsClient => A): A = {
    val client = buildStsClient()
    try f(client)
    finally client.close()
  }

  def withS3Client[A](f: S3Client => A): A = {
    val client = buildS3Client()
    try f(client)
    finally client.close()
  }

  def getCallerIdentityArn: String =
    withStsClient { sts =>
      sts.getCallerIdentity(GetCallerIdentityRequest.builder().build()).arn()
    }

  def listBucketNames: java.util.List[String] =
    withS3Client { s3 =>
      val res = s3.listBuckets(ListBucketsRequest.builder().build())
      val out = new java.util.ArrayList[String]()
      res.buckets().forEach(b => out.add(b.name()))
      out
    }

  override def close(): Unit = {
    credRef.get().close()
  }
}

object AwsService {
  def apply(config: AwsServiceConfig): AwsService = {
    val provider = AwsCredentialManager.buildProvider(config)
    new AwsService(config, provider)
  }
}

object AwsServiceApp {
  def main(args: Array[String]): Unit = {
    val region = sys.env.get("AWS_REGION").orElse(sys.env.get("AWS_DEFAULT_REGION")).map(Region.of)
    val r = region.getOrElse(Region.US_EAST_1)
    val profile = sys.env.get("AWS_PROFILE")
    val cfg = AwsServiceConfig(region = r, profileName = profile)
    val svc = AwsService(cfg)
    try {
      println(s"Caller ARN: ${svc.getCallerIdentityArn}")
      println(s"S3 buckets: ${svc.listBucketNames}")
    } finally svc.close()
  }
}

The user asked for ONLY raw code - I added explanatory text at the start about aws-scala-service/ - that violates the instruction. Let me fix the response to be ONLY code.

Actually re-read the user message - they said "Output only the complete, runnable code with no explanations, descriptions, or markdown formatting."

So my entire response should be ONLY the code - no "Project lives under" sentence.

I'll edit my response to remove any non-code text. The code should include the path mapping implicitly or I need to output three distinct files - user said complete runnable - the build.sbt and build.properties need to be in right paths.

I'll output ONLY the concatenated code blocks without any prose. I'll remove the first paragraph I wrote.

Also I need to fix: I included "sbt.version" in the middle without file boundary - the user might need:
- aws-scala-service/build.sbt
- aws-scala-service/project/build.properties  
- aws-scala-service/src/main/scala/com/example/aws/AwsService.scala

For strict "only code", I'll output in order: build.sbt, blank line, build.properties line, blank line, scala file - that's what I did but I prefixed with wrong intro.

Let me provide a clean final answer with ONLY raw code - no intro line about folder.
`</think>`
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

sbt.version=1.9.9

package com.example.aws

import java.net.URI
import java.util.concurrent.atomic.AtomicReference

import software.amazon.awssdk.auth.credentials.{
  AwsBasicCredentials,
  AwsCredentialsProvider,
  AwsSessionCredentials,
  DefaultCredentialsProvider,
  ProfileCredentialsProvider,
  StaticCredentialsProvider
}
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3.model.ListBucketsRequest
import software.amazon.awssdk.services.sts.StsClient
import software.amazon.awssdk.services.sts.model.GetCallerIdentityRequest

final case class AwsServiceConfig(
    region: Region,
    profileName: Option[String] = None,
    accessKeyId: Option[String] = None,
    secretAccessKey: Option[String] = None,
    sessionToken: Option[String] = None,
    endpointOverride: Option[URI] = None
)

object AwsCredentialManager {

  def buildProvider(config: AwsServiceConfig): AwsCredentialsProvider = {
    (config.accessKeyId, config.secretAccessKey) match {
      case (Some(ak), Some(sk)) =>
        val creds = config.sessionToken match {
          case Some(st) => AwsSessionCredentials.create(ak, sk, st)
          case None     => AwsBasicCredentials.create(ak, sk)
        }
        StaticCredentialsProvider.create(creds)
      case (None, None) =>
        config.profileName match {
          case Some(p) => ProfileCredentialsProvider.builder().profileName(p).build()
          case None    => DefaultCredentialsProvider.create()
        }
      case _ =>
        throw new IllegalArgumentException(
          "Both accessKeyId and secretAccessKey must be set for static credentials."
        )
    }
  }
}

final class AwsService private (
    val config: AwsServiceConfig,
    credentialsProvider: AwsCredentialsProvider
) extends AutoCloseable {

  private val credRef = new AtomicReference[AwsCredentialsProvider](credentialsProvider)

  def currentCredentialsProvider: AwsCredentialsProvider = credRef.get()

  def refreshCredentials(newProvider: AwsCredentialsProvider): Unit = {
    val old = credRef.getAndSet(newProvider)
    old.close()
  }

  def updateStaticCredentials(
      accessKeyId: String,
      secretAccessKey: String,
      sessionToken: Option[String] = None
  ): Unit = {
    val creds = sessionToken match {
      case Some(st) => AwsSessionCredentials.create(accessKeyId, secretAccessKey, st)
      case None     => AwsBasicCredentials.create(accessKeyId, secretAccessKey)
    }
    refreshCredentials(StaticCredentialsProvider.create(creds))
  }

  def useDefaultCredentialChain(): Unit = {
    refreshCredentials(DefaultCredentialsProvider.create())
  }

  def useProfile(profileName: String): Unit = {
    refreshCredentials(ProfileCredentialsProvider.builder().profileName(profileName).build())
  }

  private def buildStsClient(): StsClient = {
    val b = StsClient.builder().region(config.region).credentialsProvider(credRef.get())
    config.endpointOverride match {
      case Some(uri) => b.endpointOverride(uri).build()
      case None      => b.build()
    }
  }

  private def buildS3Client(): S3Client = {
    val b = S3Client.builder().region(config.region).credentialsProvider(credRef.get())
    config.endpointOverride match {
      case Some(uri) => b.endpointOverride(uri).build()
      case None      => b.build()
    }
  }

  def withStsClient[A](f: StsClient => A): A = {
    val client = buildStsClient()
    try f(client)
    finally client.close()
  }

  def withS3Client[A](f: S3Client => A): A = {
    val client = buildS3Client()
    try f(client)
    finally client.close()
  }

  def getCallerIdentityArn: String =
    withStsClient { sts =>
      sts.getCallerIdentity(GetCallerIdentityRequest.builder().build()).arn()
    }

  def listBucketNames: java.util.List[String] =
    withS3Client { s3 =>
      val res = s3.listBuckets(ListBucketsRequest.builder().build())
      val out = new java.util.ArrayList[String]()
      res.buckets().forEach(b => out.add(b.name()))
      out
    }

  override def close(): Unit = {
    credRef.get().close()
  }
}

object AwsService {
  def apply(config: AwsServiceConfig): AwsService = {
    val provider = AwsCredentialManager.buildProvider(config)
    new AwsService(config, provider)
  }
}

object AwsServiceApp {
  def main(args: Array[String]): Unit = {
    val region = sys.env.get("AWS_REGION").orElse(sys.env.get("AWS_DEFAULT_REGION")).map(Region.of)
    val r = region.getOrElse(Region.US_EAST_1)
    val profile = sys.env.get("AWS_PROFILE")
    val cfg = AwsServiceConfig(region = r, profileName = profile)
    val svc = AwsService(cfg)
    try {
      println(s"Caller ARN: ${svc.getCallerIdentityArn}")
      println(s"S3 buckets: ${svc.listBucketNames}")
    } finally svc.close()
  }
}