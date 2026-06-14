# ── ECS Cluster ───────────────────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "${var.app_name}-cluster"

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

# ── CloudWatch log group ──────────────────────────────────────────────────────
resource "aws_cloudwatch_log_group" "api" {
  name              = "/ecs/${var.app_name}-api"
  retention_in_days = 14
}

# ── IAM — ECS task execution role ─────────────────────────────────────────────
resource "aws_iam_role" "ecs_execution" {
  name = "${var.app_name}-ecs-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "ecs_execution" {
  role       = aws_iam_role.ecs_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# ── ECS Task Definition ───────────────────────────────────────────────────────
resource "aws_ecs_task_definition" "api" {
  family                   = "${var.app_name}-api"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = var.ecs_cpu
  memory                   = var.ecs_memory
  execution_role_arn       = aws_iam_role.ecs_execution.arn

  container_definitions = jsonencode([{
    name      = "api"
    image     = "${aws_ecr_repository.api.repository_url}:${var.api_image_tag}"
    essential = true

    portMappings = [{
      containerPort = 8000
      protocol      = "tcp"
    }]

    environment = [
      { name = "APP_ENV",                  value = "production" },
      { name = "OPENAI_MODEL",             value = "gpt-4o-mini" },
      { name = "OPENAI_EMBEDDING_MODEL",   value = "text-embedding-3-small" },
      { name = "MEMORY_EMBEDDING_DIM",     value = "1536" },
      { name = "ALLOWED_ORIGINS",          value = "https://${aws_cloudfront_distribution.web.domain_name}" },
      { name = "FRONTEND_URL",             value = "https://${aws_cloudfront_distribution.web.domain_name}" },
      { name = "GOOGLE_REDIRECT_URI",      value = "http://${aws_lb.api.dns_name}/api/v1/auth/google/callback" },
    ]

    secrets = [
      { name = "DATABASE_URL",         valueFrom = aws_ssm_parameter.database_url.arn },
      { name = "SECRET_KEY",           valueFrom = aws_ssm_parameter.secret_key.arn },
      { name = "OPENAI_API_KEY",       valueFrom = aws_ssm_parameter.openai_api_key.arn },
      { name = "ENCRYPTION_KEY",       valueFrom = aws_ssm_parameter.encryption_key.arn },
      { name = "GOOGLE_CLIENT_ID",     valueFrom = aws_ssm_parameter.google_client_id.arn },
      { name = "GOOGLE_CLIENT_SECRET", valueFrom = aws_ssm_parameter.google_client_secret.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.api.name
        "awslogs-region"        = var.aws_region
        "awslogs-stream-prefix" = "api"
      }
    }
  }])
}

# ── ECS Service ───────────────────────────────────────────────────────────────
resource "aws_ecs_service" "api" {
  name            = "${var.app_name}-api"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.api.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.public[*].id
    security_groups  = [aws_security_group.ecs_api.id]
    assign_public_ip = true
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.api.arn
    container_name   = "api"
    container_port   = 8000
  }

  # Allow CI/CD to update task definition without Terraform blocking
  lifecycle {
    ignore_changes = [task_definition]
  }

  depends_on = [aws_lb_listener.api_http]
}

# ── SSM Parameter Store — secrets ─────────────────────────────────────────────
resource "aws_ssm_parameter" "database_url" {
  name  = "/${var.app_name}/DATABASE_URL"
  type  = "SecureString"
  value = var.database_url
}

resource "aws_ssm_parameter" "secret_key" {
  name  = "/${var.app_name}/SECRET_KEY"
  type  = "SecureString"
  value = var.secret_key
}

resource "aws_ssm_parameter" "openai_api_key" {
  name  = "/${var.app_name}/OPENAI_API_KEY"
  type  = "SecureString"
  value = var.openai_api_key
}

resource "aws_ssm_parameter" "encryption_key" {
  name  = "/${var.app_name}/ENCRYPTION_KEY"
  type  = "SecureString"
  value = var.encryption_key
}

resource "aws_ssm_parameter" "google_client_id" {
  name  = "/${var.app_name}/GOOGLE_CLIENT_ID"
  type  = "SecureString"
  value = var.google_client_id
}

resource "aws_ssm_parameter" "google_client_secret" {
  name  = "/${var.app_name}/GOOGLE_CLIENT_SECRET"
  type  = "SecureString"
  value = var.google_client_secret
}

# Grant ECS task role access to SSM parameters
resource "aws_iam_role_policy" "ecs_ssm" {
  name = "${var.app_name}-ecs-ssm"
  role = aws_iam_role.ecs_execution.id

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
