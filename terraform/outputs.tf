output "cloudfront_url" {
  description = "Frontend URL (CloudFront)"
  value       = "https://${aws_cloudfront_distribution.web.domain_name}"
}

output "api_url" {
  description = "Backend API URL (ALB)"
  value       = "http://${aws_lb.api.dns_name}"
}

output "ecr_repository_url" {
  description = "ECR repository URL for Docker images"
  value       = aws_ecr_repository.api.repository_url
}

output "web_s3_bucket" {
  description = "S3 bucket name for frontend deployment"
  value       = aws_s3_bucket.web.bucket
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID (needed for cache invalidation)"
  value       = aws_cloudfront_distribution.web.id
}

output "lambda_code_bucket" {
  description = "S3 bucket for Lambda code packages"
  value       = aws_s3_bucket.lambda_code.bucket
}

