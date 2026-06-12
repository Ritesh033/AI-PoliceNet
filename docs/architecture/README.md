# System Architecture

## Overview

AI PoliceNet follows a microservices architecture with event-driven communication via Apache Kafka. The system is designed for high availability, scalability, and security.

## Architecture Diagram

```
                    ┌─────────────────────┐
                    │   Load Balancer      │
                    │   (AWS ALB/NLB)      │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    API Gateway       │
                    │  (Rate Limiting,     │
                    │   Auth, Routing)     │
                    └──────────┬──────────┘
                               │
         ┌─────────┬───────────┼───────────┬──────────┐
         │         │           │           │          │
    ┌────▼───┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐ ┌───▼────┐
    │ Auth   │ │Citizen │ │  FIR   │ │Evidence│ │Social  │
    │Service │ │Service │ │Service │ │Service │ │Media   │
    └────┬───┘ └───┬────┘ └───┬────┘ └───┬────┘ └───┬────┘
         │         │           │           │          │
         └─────────┴───────────┴───────────┴──────────┘
                               │
                    ┌──────────▼──────────┐
                    │    Apache Kafka      │
                    │   (Event Bus)        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
       ┌──────▼──────┐ ┌──────▼──────┐ ┌───────▼─────┐
       │ PostgreSQL  │ │  MongoDB    │ │Elasticsearch│
       │ (FIR, Auth) │ │ (Evidence)  │ │ (Search)    │
       └─────────────┘ └─────────────┘ └─────────────┘
```

## Key Design Decisions

- **Microservices**: Each domain has its own service for independent scaling
- **Event-Driven**: Kafka ensures reliable async communication between services
- **CQRS**: Separate read/write models for high-traffic modules
- **Blockchain**: Evidence integrity via immutable ledger
- **AI Pipeline**: Dedicated GPU-enabled services for ML inference

## Service Communication

| Pattern | Use Case |
|---------|----------|
| REST API | Synchronous client-server communication |
| Kafka Events | Async inter-service messaging |
| gRPC | High-performance internal service calls |
| WebSocket | Real-time notifications and alerts |

## Security Layers

1. WAF (Web Application Firewall)
2. API Gateway authentication and rate limiting
3. Service-to-service mTLS
4. Database-level encryption at rest
5. Application-level field encryption for sensitive data

## Documentation

- [Detailed Architecture](./detailed-architecture.md)
- [Service Interaction Diagrams](./service-interactions.md)
- [Data Flow Diagrams](./data-flows.md)
- [Scalability Strategy](./scalability.md)
