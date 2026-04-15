import software.amazon.awssdk.auth.credentials.{AwsBasicCredentials, DefaultCredentialsProvider, StaticCredentialsProvider}
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3.model.{ListBucketsRequest, ListObjectsV2Request, PutObjectRequest}
import software.amazon.awssdk.services.sts.StsClient
import software.amazon.awssdk.services.sts.model.GetCallerIdentityRequest
import software.amazon.awssdk.core.sync.RequestBody

import scala.util.{Try, Success, Failure}
import scala.jdk.CollectionConverters._

class AwsCredentialManager(region: Region) {

  private val defaultProvider: DefaultCredentialsProvider = DefaultCredentialsProvider.create()

  def getDefaultCredentialsProvider: DefaultCredentialsProvider = defaultProvider

  def createStaticProvider(accessKeyId: String, secretAccessKey: String): StaticCredentialsProvider = {
    require(accessKeyId.nonEmpty, "Access key ID must not be empty")
    require(secretAccessKey.nonEmpty, "Secret access key must not be empty")
    StaticCredentialsProvider.create(
      AwsBasicCredentials.create(accessKeyId, secretAccessKey)
    )
  }

  def verifyCredentials(): Try[String] = {
    Try {
      val stsClient = StsClient.builder()
        .region(region)
        .credentialsProvider(defaultProvider)
        .build()
      try {
        val identity = stsClient.getCallerIdentity(GetCallerIdentityRequest.builder().build())
        s"Verified: account=${identity.account()}, arn=${identity.arn()}"
      } finally {
        stsClient.close()
      }
    }
  }
}

class AwsS3Service(region: Region, credentialManager: AwsCredentialManager) {

  private val s3Client: S3Client = S3Client.builder()
    .region(region)
    .credentialsProvider(credentialManager.getDefaultCredentialsProvider)
    .build()

  def listBuckets(): Try[List[String]] = {
    Try {
      val response = s3Client.listBuckets(ListBucketsRequest.builder().build())
      response.buckets().asScala.map(_.name()).toList
    }
  }

  def listObjects(bucketName: String, prefix: String = ""): Try[List[String]] = {
    Try {
      val requestBuilder = ListObjectsV2Request.builder().bucket(bucketName)
      val request = if (prefix.nonEmpty) requestBuilder.prefix(prefix).build() else requestBuilder.build()
      val response = s3Client.listObjectsV2(request)
      response.contents().asScala.map(_.key()).toList
    }
  }

  def putObject(bucketName: String, key: String, content: String): Try[String] = {
    Try {
      val request = PutObjectRequest.builder()
        .bucket(bucketName)
        .key(key)
        .build()
      val response = s3Client.putObject(request, RequestBody.fromString(content))
      response.eTag()
    }
  }

  def close(): Unit = s3Client.close()
}

object AwsServiceApp {
  def main(args: Array[String]): Unit = {
    val region = Region.US_EAST_1
    val credentialManager = new AwsCredentialManager(region)

    credentialManager.verifyCredentials() match {
      case Success(msg) => println(s"Credentials OK: $msg")
      case Failure(ex)  => println(s"Credential verification failed: ${ex.getMessage}")
    }

    val s3Service = new AwsS3Service(region, credentialManager)
    try {
      s3Service.listBuckets() match {
        case Success(buckets) =>
          println(s"Found ${buckets.size} buckets:")
          buckets.foreach(b => println(s"  - $b"))
        case Failure(ex) =>
          println(s"Failed to list buckets: ${ex.getMessage}")
      }
    } finally {
      s3Service.close()
    }
  }
}