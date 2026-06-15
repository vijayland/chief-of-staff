# ── SSM Parameter Store — secrets shared by App Runner + Lambda ───────────────
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
