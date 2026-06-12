# Database

Polyglot persistence layer for AI PoliceNet.

## Databases

### PostgreSQL (Primary Relational)
- User accounts, roles, permissions
- FIR records (immutable)
- Officer profiles and integrity scores
- Disciplinary records and fines
- Audit logs

### MongoDB (Document Store)
- Evidence metadata and files
- Social media content
- AI analysis results
- Temporary evidence reviews

### Elasticsearch (Search Engine)
- Full-text search across FIRs, complaints, evidence
- Social media content indexing
- Analytics and aggregations
- Geospatial queries

### Redis (Cache & Sessions)
- User sessions
- Rate limiting counters
- Frequently accessed data cache
- Real-time notification queue

## Directory Structure
```
database/
├── postgres/      # PostgreSQL initialization scripts
├── mongodb/       # MongoDB indexes and validation rules
├── elasticsearch/ # Index templates and mappings
├── redis/         # Redis configuration
├── migrations/    # Database migration files
├── schemas/       # Schema definitions
└── backups/       # Backup configurations
```

## Migrations
Run migrations with: `npm run migrate` (from the respective service directory)
