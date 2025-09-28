terraform {
    required_version = ">= 1.5.0"
    required_providers {
        aws = {
            source = "hashicorp/aws"
            version = "~> 5.0"
        }
        random = {
            source = "hashicorp/random"
            version = "~> 3.0"
        }
    }
}

provider "aws" {
    region = var.region
}

variable "region" {
    type = string
    default = "us-east-1"
}

resource "random_id" "suffix" {
    byte_length = 3
}

locals {
    bucket_name = "tf-simple-bucket-${random_id.suffix.hex}"
}

resource "aws_s3_bucket" "this" {
    bucket = local.bucket_name
}

resource "aws_s3_bucket_public_access_block" "this" {
    bucket = aws_s3_bucket.this.id
    block_public_acls = true
    block_public_policy = true
    ignore_public_acls = true
    restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "this" {
    bucket = aws_s3_bucket.this.id
    versioning_configuration {
        status = "Enabled"
    }
}

resource "aws_s3_object" "sample1" {
    bucket = aws_s3_bucket.this.id
    key = "hello.txt"
    content = "hello from terraform\n"
}

resource "aws_s3_object" "sample2" {
    bucket = aws_s3_bucket.this.id
    key = "folder/sample.json"
    content = jsonencode({ project = "simple", ok = true })
    content_type = "application/json"
}

output "bucket_name" {
    value = aws_s3_bucket.this.bucket
}