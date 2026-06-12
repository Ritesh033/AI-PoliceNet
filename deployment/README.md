# Deployment

Deployment configurations and CI/CD pipeline for AI PoliceNet.

## Environments

| Environment | Purpose | Auto-deploy |
|-------------|---------|-------------|
| Development | Local dev and testing | N/A |
| Staging | Pre-production validation | On merge to `develop` |
| Production | Live system | Manual approval required |

## CI/CD Pipeline (GitHub Actions)

```
Push → Lint → Unit Tests → Build → Integration Tests → Security Scan
  → [staging] Auto-deploy → Smoke Tests
  → [production] Manual Approval → Deploy → Health Check
```

## Directory Structure
```
deployment/
├── development/   # Docker Compose configs for local dev
├── staging/       # Staging-specific configs
├── production/    # Production configs with HA settings
├── ci-cd/         # GitHub Actions workflow files
└── monitoring/    # Deployment monitoring and alerts
```

## Monitoring
- Health check endpoints for each service
- Prometheus metrics collection
- Grafana dashboards
- PagerDuty alerting for production issues
