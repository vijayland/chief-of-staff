# ── IAM role for all Lambda functions ────────────────────────────────────────
resource "aws_iam_role" "lambda" {
  name = "${var.app_name}-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_iam_role_policy" "lambda_ssm" {
  name = "${var.app_name}-lambda-ssm"
  role = aws_iam_role.lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["ssm:GetParameter", "ssm:GetParameters"]
      Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.app_name}/*"
    }]
  })
}

# Shared environment variables for all Lambda functions
locals {
  lambda_env = {
    APP_ENV                = "production"
    DATABASE_URL           = var.database_url
    SECRET_KEY             = var.secret_key
    OPENAI_API_KEY         = var.openai_api_key
    OPENAI_MODEL           = "gpt-4o-mini"
    OPENAI_EMBEDDING_MODEL = "text-embedding-3-small"
    ENCRYPTION_KEY         = var.encryption_key
    GOOGLE_CLIENT_ID       = var.google_client_id
    GOOGLE_CLIENT_SECRET   = var.google_client_secret
    MEMORY_EMBEDDING_DIM   = "1536"
    REDIS_URL              = var.redis_url
    CELERY_BROKER_URL      = var.celery_broker_url
    CELERY_RESULT_BACKEND  = var.celery_result_backend
  }
}

# ── Lambda: Email Sync (every 5 minutes) ─────────────────────────────────────
resource "aws_lambda_function" "email_sync" {
  function_name = "${var.app_name}-email-sync"
  role          = aws_iam_role.lambda.arn
  package_type  = "Zip"
  # CI/CD uploads the zip to S3 and updates this
  s3_bucket     = aws_s3_bucket.lambda_code.bucket
  s3_key        = "email_sync.zip"
  handler       = "lambdas.email_sync_handler.handler"
  runtime       = "python3.11"
  timeout       = 300   # 5 minutes max
  memory_size   = 512

  environment {
    variables = local.lambda_env
  }

  depends_on = [aws_s3_object.lambda_placeholder]
}

resource "aws_cloudwatch_event_rule" "email_sync" {
  name                = "${var.app_name}-email-sync"
  description         = "Trigger email sync every 5 minutes"
  schedule_expression = "rate(5 minutes)"
}

resource "aws_cloudwatch_event_target" "email_sync" {
  rule      = aws_cloudwatch_event_rule.email_sync.name
  target_id = "EmailSyncLambda"
  arn       = aws_lambda_function.email_sync.arn
}

resource "aws_lambda_permission" "email_sync" {
  statement_id  = "AllowEventBridgeEmailSync"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.email_sync.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.email_sync.arn
}

# ── Lambda: Calendar Sync (every 15 minutes) ──────────────────────────────────
resource "aws_lambda_function" "calendar_sync" {
  function_name = "${var.app_name}-calendar-sync"
  role          = aws_iam_role.lambda.arn
  package_type  = "Zip"
  s3_bucket     = aws_s3_bucket.lambda_code.bucket
  s3_key        = "calendar_sync.zip"
  handler       = "lambdas.calendar_sync_handler.handler"
  runtime       = "python3.11"
  timeout       = 300
  memory_size   = 512

  environment {
    variables = local.lambda_env
  }

  depends_on = [aws_s3_object.lambda_placeholder]
}

resource "aws_cloudwatch_event_rule" "calendar_sync" {
  name                = "${var.app_name}-calendar-sync"
  description         = "Trigger calendar sync every 15 minutes"
  schedule_expression = "rate(15 minutes)"
}

resource "aws_cloudwatch_event_target" "calendar_sync" {
  rule      = aws_cloudwatch_event_rule.calendar_sync.name
  target_id = "CalendarSyncLambda"
  arn       = aws_lambda_function.calendar_sync.arn
}

resource "aws_lambda_permission" "calendar_sync" {
  statement_id  = "AllowEventBridgeCalendarSync"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.calendar_sync.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.calendar_sync.arn
}

# ── Lambda: Memory Consolidation (nightly 2 AM UTC) ──────────────────────────
resource "aws_lambda_function" "memory_consolidation" {
  function_name = "${var.app_name}-memory-consolidation"
  role          = aws_iam_role.lambda.arn
  package_type  = "Zip"
  s3_bucket     = aws_s3_bucket.lambda_code.bucket
  s3_key        = "memory_consolidation.zip"
  handler       = "lambdas.memory_consolidation_handler.handler"
  runtime       = "python3.11"
  timeout       = 900   # 15 minutes — nightly job can take longer
  memory_size   = 512

  environment {
    variables = local.lambda_env
  }

  depends_on = [aws_s3_object.lambda_placeholder]
}

resource "aws_cloudwatch_event_rule" "memory_consolidation" {
  name                = "${var.app_name}-memory-consolidation"
  description         = "Trigger memory consolidation nightly at 2 AM UTC"
  schedule_expression = "cron(0 2 * * ? *)"
}

resource "aws_cloudwatch_event_target" "memory_consolidation" {
  rule      = aws_cloudwatch_event_rule.memory_consolidation.name
  target_id = "MemoryConsolidationLambda"
  arn       = aws_lambda_function.memory_consolidation.arn
}

resource "aws_lambda_permission" "memory_consolidation" {
  statement_id  = "AllowEventBridgeMemoryConsolidation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.memory_consolidation.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.memory_consolidation.arn
}

# ── S3 bucket for Lambda code packages ───────────────────────────────────────
resource "aws_s3_bucket" "lambda_code" {
  bucket = "${var.app_name}-lambda-code-${data.aws_caller_identity.current.account_id}"
}

resource "aws_s3_bucket_public_access_block" "lambda_code" {
  bucket                  = aws_s3_bucket.lambda_code.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Placeholder zips so Terraform can create Lambdas on first apply
# CI/CD replaces these with real code on every deploy
resource "aws_s3_object" "lambda_placeholder" {
  bucket  = aws_s3_bucket.lambda_code.bucket
  key     = "email_sync.zip"
  content = ""
}

resource "aws_s3_object" "lambda_placeholder_calendar" {
  bucket  = aws_s3_bucket.lambda_code.bucket
  key     = "calendar_sync.zip"
  content = ""
}

resource "aws_s3_object" "lambda_placeholder_memory" {
  bucket  = aws_s3_bucket.lambda_code.bucket
  key     = "memory_consolidation.zip"
  content = ""
}
