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
