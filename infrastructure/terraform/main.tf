# AI PoliceNet - Terraform Root Module

terraform {
  required_version = ">= 1.6.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "ai-policenet-terraform-state"
    key            = "infrastructure/terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "ai-policenet-terraform-locks"
    encrypt        = true
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "AI-PoliceNet"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}

# TODO: Add module references for VPC, EKS, RDS, etc.
