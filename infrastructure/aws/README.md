# AWS Infrastructure

## Overview

AI PoliceNet runs on AWS with the following services:

## Services Used

| AWS Service | Purpose |
|-------------|---------|
| EKS | Kubernetes cluster for microservices |
| RDS | Managed PostgreSQL |
| DocumentDB | Managed MongoDB-compatible |
| ElastiCache | Managed Redis |
| S3 | Evidence storage, backups |
| MSK | Managed Kafka |
| OpenSearch | Managed Elasticsearch |
| CloudFront | CDN for frontend |
| Route 53 | DNS management |
| ACM | SSL certificates |
| KMS | Key management |
| CloudWatch | Monitoring and logging |
| WAF | Web application firewall |
| Shield | DDoS protection |
| SES | Email service |
| SNS | Push notifications |
| Lambda | Serverless functions |

## Architecture

```
Internet → CloudFront → ALB → EKS Cluster
                                    │
                         ┌──────────┼──────────┐
                         │          │          │
                        RDS    DocumentDB   ElastiCache
                                    │
                                   MSK
                                    │
                                   S3
```

## Region

Primary: `ap-south-1` (Mumbai)
DR: `ap-southeast-1` (Singapore)

## Setup

See [Terraform configurations](../terraform/) for infrastructure-as-code.
