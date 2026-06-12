# API Gateway

Central entry point for all AI PoliceNet API requests.

## Responsibilities
- Request routing to downstream microservices
- Authentication and authorization
- Rate limiting and throttling
- Request/response logging
- CORS handling
- API versioning

## Tech Stack
- Node.js, Express.js, TypeScript
- Redis for rate limiting and caching

## Port: 8080

## Getting Started
```bash
cd backend/api-gateway
npm install
npm run dev
```
