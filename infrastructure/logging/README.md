# Logging Infrastructure

## Stack
- **Filebeat** — Log collection from containers
- **Logstash** — Log processing and enrichment
- **Elasticsearch** — Log storage and indexing
- **Kibana** — Log visualization and search

## Log Levels
- `ERROR` — System errors requiring attention
- `WARN` — Potential issues
- `INFO` — Normal operations
- `DEBUG` — Detailed debugging (dev only)

## Log Format (JSON)
```json
{
  "timestamp": "2026-01-01T00:00:00Z",
  "level": "INFO",
  "service": "fir-service",
  "trace_id": "abc123",
  "user_id": "user-456",
  "action": "fir.create",
  "message": "FIR created successfully",
  "metadata": {}
}
```

## Retention
- Development: 7 days
- Staging: 30 days
- Production: 365 days (compliance requirement)
