# Kubernetes

Kubernetes manifests for deploying AI PoliceNet on AWS EKS.

## Structure
```
kubernetes/
├── namespace.yaml
├── configmaps/
├── secrets/           # (gitignored)
├── deployments/
├── services/
├── ingress/
├── hpa/               # Horizontal Pod Autoscaler
├── pdb/               # Pod Disruption Budget
└── network-policies/
```

## Namespace
All resources are deployed to the `ai-policenet` namespace.

## Quick Deploy
```bash
kubectl apply -f kubernetes/namespace.yaml
kubectl apply -f kubernetes/configmaps/
kubectl apply -f kubernetes/secrets/
kubectl apply -f kubernetes/deployments/
kubectl apply -f kubernetes/services/
kubectl apply -f kubernetes/ingress/
```

## Scaling
- Horizontal Pod Autoscaler configured for each service
- Min: 2 replicas, Max: 10 replicas (configurable)
- Scale on CPU (70%) and memory (80%) thresholds
