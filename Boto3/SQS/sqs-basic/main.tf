terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
  }
}

provider "aws" {
  region = var.region
}

variable "region" {
  type    = string
  default = "us-east-1"
}

resource "random_id" "suffix" {
  byte_length = 3
}

locals {
  base_name = "sqs-basic-${random_id.suffix.hex}"
}

# Dead-letter queue 
resource "aws_sqs_queue" "dlq" {
  name                      = "${local.base_name}-dlq"
  message_retention_seconds = 1209600 #14 days
}

# Main queue
resource "aws_sqs_queue" "main" {
  name                       = local.base_name
  visibility_timeout_seconds = 30 # how long a received msg is hidden before it reappears
  receive_wait_time_seconds  = 10 # enable long polling 
  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

output "queue_url" {
  value = aws_sqs_queue.main.url
}
output "queue_arn" {
  value = aws_sqs_queue.main.arn
}
output "queue_name" {
  value = aws_sqs_queue.main.name
}