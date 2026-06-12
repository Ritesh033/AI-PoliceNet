# Data Pipeline

Event-driven data pipeline for real-time processing and analytics.

## Components

### Apache Kafka
- Central event bus for inter-service communication
- Topics for FIR events, evidence events, social media events, alerts
- Consumer groups for each downstream service

### Stream Processing
- Real-time event processing
- Data transformation and enrichment
- Aggregation for analytics

### Event Bus
- Service-to-service event routing
- Event sourcing for audit trails
- Dead letter queues for failed events

### Data Lake
- Raw data storage for analytics and ML training
- Parquet format for efficient querying
- Data lifecycle management

## Key Topics
| Topic | Description |
|-------|-------------|
| `fir.created` | New FIR registered |
| `fir.updated` | FIR status changed |
| `evidence.uploaded` | New evidence submitted |
| `evidence.verified` | Evidence verification complete |
| `social-media.flagged` | Content flagged by AI |
| `alert.emergency` | Emergency alert triggered |
| `notification.send` | Notification delivery request |
