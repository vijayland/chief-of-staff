# ── IAM: App Runner access role (pulls image from ECR) ───────────────────────
resource "aws_iam_role" "apprunner_access" {
  name = "${var.app_name}-apprunner-access"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "build.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr" {
  role       = aws_iam_role.apprunner_access.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# ── IAM: App Runner instance role (container reads SSM secrets) ───────────────
resource "aws_iam_role" "apprunner_instance" {
  name = "${var.app_name}-apprunner-instance"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "tasks.apprunner.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "apprunner_ssm" {
  name = "${var.app_name}-apprunner-ssm"
  role = aws_iam_role.apprunner_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["ssm:GetParameters", "ssm:GetParameter"]
      Resource = [
        aws_ssm_parameter.database_url.arn,
        aws_ssm_parameter.secret_key.arn,
        aws_ssm_parameter.openai_api_key.arn,
        aws_ssm_parameter.encryption_key.arn,
        aws_ssm_parameter.google_client_id.arn,
        aws_ssm_parameter.google_client_secret.arn,
      ]
    }]
  })
}

# ── App Runner service ────────────────────────────────────────────────────────
resource "aws_apprunner_service" "api" {
  service_name = "${var.app_name}-api"

  source_configuration {
    authentication_configuration {
      access_role_arn = aws_iam_role.apprunner_access.arn
    }

    image_repository {
      image_configuration {
        port = "8000"

        runtime_environment_variables = {
          APP_ENV                = "production"
          OPENAI_MODEL           = "gpt-4o-mini"
          OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
          MEMORY_EMBEDDING_DIM   = "1536"
          ALLOWED_ORIGINS        = "https://${aws_cloudfront_distribution.web.domain_name}"
          FRONTEND_URL           = "https://${aws_cloudfront_distribution.web.domain_name}"
          GOOGLE_REDIRECT_URI    = "https://${aws_cloudfront_distribution.web.domain_name}/api/v1/auth/google/callback"
          REDIS_URL              = var.redis_url
          CELERY_BROKER_URL      = var.celery_broker_url
          CELERY_RESULT_BACKEND  = var.celery_result_backend
        }

        runtime_environment_secrets = {
          DATABASE_URL         = aws_ssm_parameter.database_url.arn
          SECRET_KEY           = aws_ssm_parameter.secret_key.arn
          OPENAI_API_KEY       = aws_ssm_parameter.openai_api_key.arn
          ENCRYPTION_KEY       = aws_ssm_parameter.encryption_key.arn
          GOOGLE_CLIENT_ID     = aws_ssm_parameter.google_client_id.arn
          GOOGLE_CLIENT_SECRET = aws_ssm_parameter.google_client_secret.arn
        }
      }

      image_identifier      = "${aws_ecr_repository.api.repository_url}:latest"
      image_repository_type = "ECR"
    }

    # Auto-deploy whenever a new :latest image is pushed to ECR
    auto_deployments_enabled = true
  }

  instance_configuration {
    cpu               = "0.25 vCPU"
    memory            = "0.5 GB"
    instance_role_arn = aws_iam_role.apprunner_instance.arn
  }

  health_check_configuration {
    path     = "/health"
    protocol = "HTTP"
    interval = 10
    timeout  = 5
  }
}
