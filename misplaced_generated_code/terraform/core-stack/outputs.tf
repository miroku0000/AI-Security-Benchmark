output "vpc_id" {
  value = aws_vpc.main.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  value = aws_subnet.private[*].id
}

output "ec2_instance_ids" {
  value = aws_instance.app[*].id
}

output "ec2_public_ips" {
  value = aws_instance.app[*].public_ip
}

output "rds_endpoint" {
  value = aws_db_instance.main.address
}

output "rds_port" {
  value = aws_db_instance.main.port
}

output "s3_bucket_assets" {
  value = aws_s3_bucket.app_assets.bucket
}

output "s3_bucket_uploads" {
  value = aws_s3_bucket.app_uploads.bucket
}
