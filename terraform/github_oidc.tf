# GitHub Actions OIDC — lets CI authenticate to AWS without static access keys
# This creates:
#   - An OIDC identity provider for token.actions.githubusercontent.com
#   - An IAM role that GitHub Actions can assume (scoped to this repo's main branch)
#
# Usage in GitHub Actions:
#   permissions: { id-token: write, contents: read }
#   uses: aws-actions/configure-aws-credentials@v4
#   with: { role-to-assume: ${{ secrets.AWS_DEPLOY_ROLE_ARN }}, aws-region: us-east-1 }
#
# After first `terraform apply`, copy the output `deploy_role_arn` into
# the GitHub repo secret AWS_DEPLOY_ROLE_ARN.

variable "github_repo" {
  description = "GitHub repo in owner/name format (e.g. vijayethuraj/chief-of-staff)"
  type        = string
  default     = "vijayethuraj/chief-of-staff"
}

resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_deploy" {
  name = "${var.app_name}-github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        StringLike = {
          # Only the main branch of your repo can assume this role
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repo}:ref:refs/heads/main"
        }
      }
    }]
  })
}

# Inline policy — all permissions CI/CD needs
resource "aws_iam_role_policy" "github_deploy" {
  name = "${var.app_name}-github-deploy-policy"
  role = aws_iam_role.github_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      # ECR — push images
      {
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:GetDownloadUrlForLayer",
          "ecr:BatchGetImage",
          "ecr:InitiateLayerUpload",
          "ecr:UploadLayerPart",
          "ecr:CompleteLayerUpload",
          "ecr:PutImage",
        ]
        Resource = aws_ecr_repository.api.arn
      },
      # ECS — force deploy
      {
        Effect = "Allow"
        Action = [
          "ecs:UpdateService",
          "ecs:DescribeServices",
          "ecs:RegisterTaskDefinition",
          "ecs:DescribeTaskDefinition",
        ]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole"]
        Resource = aws_iam_role.ecs_execution.arn
      },
      # S3 — sync frontend
      {
        Effect = "Allow"
        Action = ["s3:PutObject", "s3:DeleteObject", "s3:ListBucket", "s3:GetObject"]
        Resource = [
          aws_s3_bucket.web.arn,
          "${aws_s3_bucket.web.arn}/*",
          aws_s3_bucket.lambda_code.arn,
          "${aws_s3_bucket.lambda_code.arn}/*",
        ]
      },
      # CloudFront — cache invalidation
      {
        Effect   = "Allow"
        Action   = ["cloudfront:CreateInvalidation"]
        Resource = aws_cloudfront_distribution.web.arn
      },
      # Lambda — update function code
      {
        Effect = "Allow"
        Action = [
          "lambda:UpdateFunctionCode",
          "lambda:GetFunction",
        ]
        Resource = [
          aws_lambda_function.email_sync.arn,
          aws_lambda_function.calendar_sync.arn,
          aws_lambda_function.memory_consolidation.arn,
        ]
      },
      # SSM — Terraform reads/writes secrets
      {
        Effect   = "Allow"
        Action   = ["ssm:GetParameter", "ssm:GetParameters", "ssm:PutParameter", "ssm:DeleteParameter"]
        Resource = "arn:aws:ssm:${var.aws_region}:${data.aws_caller_identity.current.account_id}:parameter/${var.app_name}/*"
      },
      # Terraform state backend
      {
        Effect   = "Allow"
        Action   = ["s3:GetObject", "s3:PutObject", "s3:ListBucket"]
        Resource = [
          "arn:aws:s3:::chief-of-staff-terraform-state",
          "arn:aws:s3:::chief-of-staff-terraform-state/*",
        ]
      },
    ]
  })
}

output "deploy_role_arn" {
  description = "Copy this into GitHub secret AWS_DEPLOY_ROLE_ARN"
  value       = aws_iam_role.github_deploy.arn
}
