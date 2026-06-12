# Database Design

## Overview

AI PoliceNet uses a polyglot persistence strategy with four database technologies, each chosen for specific use cases.

## Database Selection

| Database | Use Case | Data Type |
|----------|----------|-----------|
| PostgreSQL | FIRs, users, accountability, audit logs | Structured, relational |
| MongoDB | Evidence metadata, social media data | Semi-structured, documents |
| Elasticsearch | Full-text search, analytics | Search indexes |
| Redis | Sessions, caching, rate limiting | Key-value, ephemeral |

## PostgreSQL Schema (Core)

### Users & Authentication
- `users` — User accounts (citizens, officers, admins)
- `roles` — Role definitions (citizen, officer, inspector, admin, judge)
- `user_roles` — User-role assignments
- `sessions` — Active sessions
- `mfa_config` — Multi-factor authentication settings
- `otp_tokens` — One-time password tokens

### FIR Management
- `firs` — First Information Reports (tamper-proof)
- `fir_amendments` — Court-authorized FIR modifications
- `fir_status_history` — Status change audit trail
- `fir_assignments` — Officer-FIR assignments

### Accountability
- `officers` — Officer profiles and batch numbers
- `integrity_scores` — Officer integrity scores
- `misconduct_reports` — Misconduct complaints
- `disciplinary_actions` — Disciplinary records
- `officer_fines` — Fine records for false FIRs

### Audit
- `access_logs` — System access logs
- `activity_logs` — User activity logs
- `compliance_records` — Compliance audit records

## MongoDB Collections (Evidence & Media)

- `evidence` — Evidence files and metadata
- `evidence_chain` — Chain of custody records
- `social_media_content` — Flagged social media posts
- `media_analysis` — AI analysis results
- `temporary_evidence` — Under-review evidence (3-5 day period)

## Key Design Principles

1. **Immutability**: FIR records are append-only; modifications require court authorization
2. **Audit Trail**: Every data change is logged with timestamp and actor
3. **Encryption**: Sensitive fields are encrypted at the application level
4. **Partitioning**: Large tables are partitioned by date/region
5. **Soft Deletes**: No hard deletes; records are marked inactive

## Documentation

- [Entity Relationship Diagrams](./erd.md)
- [Migration Guide](./migrations.md)
- [Index Strategy](./indexes.md)
- [Backup & Recovery](./backup-strategy.md)
