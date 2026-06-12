# Networking

## VPC Configuration
- CIDR: 10.0.0.0/16
- Public subnets: 10.0.1.0/24, 10.0.2.0/24 (load balancers, NAT gateways)
- Private subnets: 10.0.10.0/24, 10.0.11.0/24 (application services)
- Database subnets: 10.0.20.0/24, 10.0.21.0/24 (isolated, no internet access)

## Security Groups
- ALB: Allow 80, 443 from internet
- Application: Allow from ALB only
- Database: Allow from application subnets only
- Kafka: Allow from application subnets only

## DNS
- Route 53 for domain management
- Internal DNS for service discovery
