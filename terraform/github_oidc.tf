# GitHub Actions OIDC — lets CI authenticate to AWS without static access keys
# This creates:
#   - An IAM role that GitHub Actions can assume (scoped to this repo's main branch)
#
# NOTE: The OIDC provider for token.actions.githubusercontent.com is a singleton
# per AWS account — we reference the existing one via data source instead of
# trying to create it (which fails with 409 if already present).

variable "github_repo" {
  description = "GitHub repo in owner/name format (e.g. vijayland/chief-of-staff)"
  type        = string
  default     = "vijayland/chief-of-staff"
}

# Reference existing OIDC provider — only one can exist per account
data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_deploy" {
  name = "${var.app_name}-github-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = data.aws_iam_openid_connect_provider.github.arn
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

# Inline policy — all permissions CI/CD + Terraform need
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
          "ecr:*",
        ]
        Resource = "*"
      },
      # ECS — create cluster, services, task definitions, force deploy
      {
        Effect   = "Allow"
        Action   = ["ecs:*"]
        Resource = "*"
      },
      {
        Effect   = "Allow"
        Action   = ["iam:PassRole", "iam:CreateRole", "iam:DeleteRole",
                    "iam:GetRole", "iam:AttachRolePolicy", "iam:DetachRolePolicy",
                    "iam:PutRolePolicy", "iam:DeleteRolePolicy", "iam:GetRolePolicy",
                    "iam:ListAttachedRolePolicies", "iam:ListRolePolicies",
                    "iam:TagRole", "iam:UntagRole", "iam:CreateInstanceProfile",
                    "iam:DeleteInstanceProfile", "iam:AddRoleToInstanceProfile",
                    "iam:RemoveRoleFromInstanceProfile", "iam:GetInstanceProfile",
                    "iam:CreateOpenIDConnectProvider", "iam:GetOpenIDConnectProvider",
                    "iam:DeleteOpenIDConnectProvider", "iam:TagOpenIDConnectProvider"]
        Resource = "*"
      },
      # EC2 / VPC — full access for Terraform networking
      {
        Effect   = "Allow"
        Action   = ["ec2:*"]
        Resource = "*"
      },
      # S3 — sync frontend + lambda code + terraform state
      {
        Effect   = "Allow"
        Action   = ["s3:*"]
        Resource = "*"
      },
      # CloudFront — distributions + cache invalidation
      {
        Effect   = "Allow"
        Action   = ["cloudfront:*"]
        Resource = "*"
      },
      # Lambda — create/update functions
      {
        Effect   = "Allow"
        Action   = ["lambda:*"]
        Resource = "*"
      },
      # EventBridge — schedule rules (requires events:TagResource for default_tags)
      {
        Effect   = "Allow"
        Action   = ["events:*"]
        Resource = "*"
      },
      # ElastiCache — Redis cluster
      {
        Effect   = "Allow"
        Action   = ["elasticache:*"]
        Resource = "*"
      },
      # CloudWatch Logs — ECS + Lambda log groups
      {
        Effect   = "Allow"
        Action   = ["logs:*"]
        Resource = "*"
      },
      # SSM — Terraform reads/writes secrets
      {
        Effect   = "Allow"
        Action   = ["ssm:*"]
        Resource = "*"
      },
    ]
  })
}

output "deploy_role_arn" {
  description = "Copy this into GitHub secret AWS_DEPLOY_ROLE_ARN"
  value       = aws_iam_role.github_deploy.arn
}
