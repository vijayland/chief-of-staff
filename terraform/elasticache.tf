# ── ElastiCache Redis — session cache + OAuth state store ─────────────────────

# Private subnets — ElastiCache must NOT be publicly accessible
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.${count.index + 10}.0/24"
  availability_zone = data.aws_availability_zones.available.names[count.index]
}

# ElastiCache requires a subnet group spanning 2+ AZs
resource "aws_elasticache_subnet_group" "redis" {
  name       = "${var.app_name}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

# Security group — only ECS and Lambda can reach Redis on port 6379
resource "aws_security_group" "redis" {
  name   = "${var.app_name}-redis-sg"
  vpc_id = aws_vpc.main.id

  ingress {
    description     = "Redis from ECS"
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.ecs_api.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# ElastiCache Redis cluster (single node — cost effective for interview/MVP)
resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${var.app_name}-redis"
  engine               = "redis"
  node_type            = "cache.t3.micro"   # cheapest — ~$12/month
  num_cache_nodes      = 1
  parameter_group_name = "default.redis7"
  engine_version       = "7.1"
  port                 = 6379
  subnet_group_name    = aws_elasticache_subnet_group.redis.name
  security_group_ids   = [aws_security_group.redis.id]
}

# Store Redis URL in SSM so ECS + Lambda can read it
resource "aws_ssm_parameter" "redis_url" {
  name  = "/${var.app_name}/REDIS_URL"
  type  = "SecureString"
  value = "redis://${aws_elasticache_cluster.redis.cache_nodes[0].address}:6379/0"
}
