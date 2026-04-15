import scala.jdk.CollectionConverters._
import software.amazon.awssdk.auth.credentials._
import software.amazon.awssdk.core.exception.SdkException
import software.amazon.awssdk.regions.Region
import software.amazon.awssdk.services.s3.S3Client
import software.amazon.awssdk.services.s3.model.{Bucket, S3Exception}
import software.amazon.awssdk.services.sts.StsClient
import software.amazon.awssdk.services.sts.model.StsException