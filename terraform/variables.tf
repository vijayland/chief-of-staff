variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "app_name" {
  description = "Application name used as prefix for all resources"
  type        = string
  default     = "chief-of-staff"
}

variable "environment" {
  description = "Deployment environment"
  type        = string
  default     = "production"
}

# ── ECR / App Runner ──────────────────────────────────────────────────────────
variable "api_image_tag" {
  description = "Docker image tag to deploy (injected by CI/CD)"
  type        = string
  default     = "latest"
}

# ── App secrets (set via TF_VAR_* env vars in CI/CD) ─────────────────────────
variable "database_url" {
  description = "PostgreSQL connection string (Neon)"
  type        = string
  sensitive   = true
}

variable "secret_key" {
  description = "JWT secret key"
  type        = string
  sensitive   = true
}

variable "openai_api_key" {
  description = "OpenAI API key"
  type        = string
  sensitive   = true
}

variable "encryption_key" {
  description = "Fernet encryption key for OAuth tokens"
  type        = string
  sensitive   = true
}

variable "google_client_id" {
  description = "Google OAuth client ID"
  type        = string
  sensitive   = true
}

variable "google_client_secret" {
  description = "Google OAuth client secret"
  type        = string
  sensitive   = true
}

variable "redis_url" {
  description = "Redis Cloud connection URL (rediss://...)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "celery_broker_url" {
  description = "Celery broker URL (Redis db 1)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "celery_result_backend" {
  description = "Celery result backend URL (Redis db 2)"
  type        = string
  sensitive   = true
  default     = ""
}

variable "neo4j_uri" {
  description = "Neo4j connection URI"
  type        = string
  default     = ""
}

variable "neo4j_password" {
  description = "Neo4j password"
  type        = string
  sensitive   = true
  default     = ""
}
