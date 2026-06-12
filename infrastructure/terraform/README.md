# Terraform Infrastructure

## Overview

Infrastructure as Code for AI PoliceNet using Terraform.

## Structure

```
terraform/
├── main.tf           # Root module
├── variables.tf      # Input variables
├── outputs.tf        # Output values
├── providers.tf      # Provider configuration
├── modules/
│   ├── vpc/          # VPC and networking
│   ├── eks/          # Kubernetes cluster
│   ├── rds/          # PostgreSQL
│   ├── documentdb/   # MongoDB-compatible
│   ├── elasticache/  # Redis
│   ├── s3/           # Object storage
│   ├── msk/          # Kafka
│   ├── opensearch/   # Elasticsearch
│   └── monitoring/   # CloudWatch, Prometheus
└── environments/
    ├── dev/
    ├── staging/
    └── production/
```

## Usage

```bash
# Initialize
terraform init

# Plan
terraform plan -var-file=environments/dev/terraform.tfvars

# Apply
terraform apply -var-file=environments/dev/terraform.tfvars

# Destroy (development only)
terraform destroy -var-file=environments/dev/terraform.tfvars
```

## State Management

Terraform state is stored in S3 with DynamoDB locking.
