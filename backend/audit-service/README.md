# Audit Service

Maintains immutable audit logs for all system activities and compliance tracking.

## Features
- **Access Logs**: Track who accessed what and when
- **Activity Logs**: Record all user actions
- **Compliance**: Ensure regulatory compliance with automated checks

## Log Types
| Log Type | Description | Retention |
|----------|-------------|-----------|
| Access Log | Login/logout, data access | 365 days |
| Activity Log | CRUD operations, status changes | 365 days |
| Compliance Log | Policy violations, audit findings | Indefinite |
| Security Log | Auth failures, suspicious activity | 365 days |

## Key Principles
1. Logs are **append-only** (immutable)
2. Logs are cryptographically signed
3. No user can delete or modify audit logs
4. Tamper detection via hash chains

## Port: 8011
