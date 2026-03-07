# Kubernetes Deployment Guide

This guide covers deploying the Raster to SVG Converter to a Kubernetes cluster.

## Prerequisites

- Kubernetes 1.24+
- kubectl configured to your cluster
- Nginx Ingress Controller installed
- cert-manager for SSL/TLS
- Minimum 4 CPU and 8GB RAM

## Files

All Kubernetes manifests are in the `k8s/` directory:

- `namespace.yaml` - raster-svg namespace
- `redis-deployment.yaml` - Redis with persistent storage
- `api-deployment.yaml` - FastAPI backend (3 replicas)
- `worker-deployment.yaml` - Celery workers (4 replicas, HPA 2-10)
- `frontend-deployment.yaml` - Next.js frontend (2 replicas, HPA 2-5)
- `ingress.yaml` - Ingress controller with SSL/TLS

## Quick Start

### 1. Prerequisites

Install Nginx and cert-manager:

```bash
# Nginx Ingress Controller
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm install nginx-ingress ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace

# cert-manager
helm repo add jetstack https://charts.jetstack.io
helm install cert-manager jetstack/cert-manager \
  --namespace cert-manager --create-namespace \
  --set installCRDs=true
```

### 2. Configure Domains

Update domain names in manifests:

```bash
cd k8s
sed -i 's/example.com/your-domain.com/g' *.yaml
sed -i 's/admin@example.com/your-email@example.com/g' ingress.yaml
sed -i 's|ghcr.io/YOUR_REPO|ghcr.io/your-user|g' *.yaml
```

### 3. Deploy

```bash
# Deploy all components
kubectl apply -f namespace.yaml
kubectl apply -f redis-deployment.yaml
kubectl apply -f api-deployment.yaml
kubectl apply -f worker-deployment.yaml
kubectl apply -f frontend-deployment.yaml
kubectl apply -f ingress.yaml

# Verify
kubectl get pods -n raster-svg
kubectl get ingress -n raster-svg
```

### 4. Configure DNS

Point your domains to the Ingress IP:

```bash
# Get Ingress IP
kubectl get ingress -n raster-svg -o wide

# Update DNS:
# api.your-domain.com → <INGRESS_IP>
# app.your-domain.com → <INGRESS_IP>
```

## Verification

```bash
# Check all components
kubectl get all -n raster-svg

# Test API health
curl https://api.your-domain.com/health

# Check logs
kubectl logs -n raster-svg -l app=api --tail=50
```

## Scaling

### Manual Scaling

```bash
kubectl scale deployment api --replicas=5 -n raster-svg
kubectl scale deployment worker --replicas=8 -n raster-svg
kubectl scale deployment frontend --replicas=4 -n raster-svg
```

### Auto-Scaling

HPA is configured:
- **Workers**: CPU 70%, Memory 80%, replicas 2-10
- **Frontend**: CPU 75%, replicas 2-5

```bash
# Monitor HPA
kubectl get hpa -n raster-svg -w
```

## Updates

### Rolling Update

```bash
# Update images
kubectl set image deployment/api \
  api=ghcr.io/your-repo/backend:v1.2.0 \
  -n raster-svg

# Monitor rollout
kubectl rollout status deployment/api -n raster-svg

# Rollback if needed
kubectl rollout undo deployment/api -n raster-svg
```

## Monitoring

Access monitoring services:

```bash
# Prometheus
kubectl port-forward svc/prometheus 9090:9090 -n raster-svg

# Grafana
kubectl port-forward svc/grafana 3000:3000 -n raster-svg

# Flower
kubectl port-forward svc/flower 5555:5555 -n raster-svg
```

## Troubleshooting

```bash
# Check pod status
kubectl describe pod <pod-name> -n raster-svg

# View logs
kubectl logs <pod-name> -n raster-svg

# Check events
kubectl get events -n raster-svg --sort-by='.lastTimestamp'

# Test connectivity
kubectl run -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl http://api:8000/health
```

## Cleanup

```bash
# Remove all resources
kubectl delete namespace raster-svg
```

## Reference

- [Kubernetes Documentation](https://kubernetes.io/docs/)
- [cert-manager](https://cert-manager.io/)
- [Nginx Ingress Controller](https://kubernetes.github.io/ingress-nginx/)
