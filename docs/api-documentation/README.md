# API Documentation

## Overview

AI PoliceNet exposes RESTful APIs through a centralized API Gateway. All endpoints require authentication unless explicitly marked as public.

## Base URL

```
Production:  https://api.ai-policenet.gov/v1
Staging:     https://staging-api.ai-policenet.gov/v1
Development: http://localhost:8080/v1
```

## Authentication

All API requests require a JWT bearer token:

```
Authorization: Bearer <token>
```

## API Modules

### Authentication Service (`/auth`)
- `POST /auth/register` — Register a new user
- `POST /auth/login` — Login with credentials
- `POST /auth/otp/send` — Send OTP for verification
- `POST /auth/otp/verify` — Verify OTP
- `POST /auth/mfa/setup` — Setup multi-factor authentication
- `POST /auth/refresh` — Refresh access token
- `POST /auth/logout` — Invalidate session

### Citizen Service (`/citizens`)
- `GET /citizens/profile` — Get citizen profile
- `PUT /citizens/profile` — Update citizen profile
- `POST /citizens/complaints` — File a new complaint
- `GET /citizens/complaints` — List citizen complaints
- `GET /citizens/complaints/:id` — Get complaint details
- `POST /citizens/reports` — Submit a report

### FIR Service (`/fir`)
- `POST /fir` — Register a new FIR
- `GET /fir/:id` — Get FIR details
- `GET /fir/:id/audit` — Get FIR audit trail
- `GET /fir/:id/timeline` — Get FIR timeline
- `PUT /fir/:id/status` — Update FIR status (authorized roles only)
- `GET /fir/search` — Search FIRs

### Evidence Service (`/evidence`)
- `POST /evidence/upload` — Upload evidence
- `GET /evidence/:id` — Get evidence details
- `GET /evidence/:id/chain-of-custody` — Get custody chain
- `POST /evidence/:id/verify` — Verify evidence hash
- `GET /evidence/search` — Search evidence

### Social Media Service (`/social-media`)
- `GET /social-media/flags` — Get flagged content
- `GET /social-media/flags/:id` — Get flag details
- `POST /social-media/flags/:id/review` — Review flagged content
- `GET /social-media/analytics` — Get social media analytics

### Accountability Service (`/accountability`)
- `GET /accountability/officers/:id/score` — Get officer integrity score
- `GET /accountability/officers/:id/reviews` — Get officer reviews
- `POST /accountability/misconduct` — Report misconduct
- `GET /accountability/disciplinary` — Get disciplinary records

### Notification Service (`/notifications`)
- `GET /notifications` — List user notifications
- `PUT /notifications/:id/read` — Mark notification as read
- `POST /notifications/emergency` — Send emergency alert

## Rate Limits

| Role | Requests/min |
|------|-------------|
| Citizen | 60 |
| Officer | 120 |
| Admin | 300 |
| System | Unlimited |

## Error Codes

| Code | Description |
|------|-------------|
| 400 | Bad Request |
| 401 | Unauthorized |
| 403 | Forbidden |
| 404 | Not Found |
| 409 | Conflict |
| 429 | Rate Limited |
| 500 | Internal Server Error |

## Documentation

- [OpenAPI Spec](./openapi.yaml)
- [Postman Collection](./postman-collection.json)
- [WebSocket Events](./websocket-events.md)
