# Backup & Recovery

## Backup Strategy

| Resource | Frequency | Retention | Method |
|----------|-----------|-----------|--------|
| PostgreSQL | Daily + WAL | 30 days | AWS RDS automated snapshots |
| MongoDB | Daily | 30 days | mongodump to S3 |
| Elasticsearch | Daily | 14 days | Snapshot to S3 |
| Evidence files | Continuous | Indefinite | S3 versioning + cross-region replication |
| Blockchain ledger | Real-time | Indefinite | Multi-node replication |

## Recovery Procedures

1. **Database Recovery**: Restore from RDS snapshot
2. **Evidence Recovery**: Restore from S3 versioned objects
3. **Full Disaster Recovery**: Failover to DR region (ap-southeast-1)

## RPO/RTO Targets

| Metric | Target |
|--------|--------|
| Recovery Point Objective (RPO) | < 1 hour |
| Recovery Time Objective (RTO) | < 4 hours |

## Testing
- Monthly backup restoration tests
- Quarterly DR failover drills
