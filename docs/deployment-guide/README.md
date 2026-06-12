# Deployment Guide

## Overview

AI PoliceNet supports deployment on AWS using Docker containers orchestrated by Kubernetes.

## Environments

| Environment | Purpose | URL |
|-------------|---------|-----|
| Development | Local development | localhost |
| Staging | Pre-production testing | staging.ai-policenet.gov |
| Production | Live system | ai-policenet.gov |

## Prerequisites

- Docker >= 24.x
- Kubernetes >= 1.28
- Helm >= 3.13
- AWS CLI configured
- Terraform >= 1.6

## Local Development

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Kubernetes Deployment

```bash
# Apply namespace
kubectl apply -f kubernetes/namespace.yaml

# Deploy secrets
kubectl apply -f kubernetes/secrets/

# Deploy services
kubectl apply -f kubernetes/

# Check status
kubectl get pods -n ai-policenet
```

## CI/CD Pipeline

1. Code push triggers CI pipeline
2. Automated tests (unit, integration, security)
3. Docker image build and push
4. Staging deployment (automatic)
5. Production deployment (manual approval required)

## Monitoring

- Prometheus for metrics collection
- Grafana for dashboards
- ELK Stack for centralized logging
- PagerDuty for alerting

## Documentation

- [AWS Infrastructure Setup](./aws-setup.md)
- [Kubernetes Configuration](./kubernetes-config.md)
- [CI/CD Pipeline](./cicd-pipeline.md)
- [Rollback Procedures](./rollback.md)
