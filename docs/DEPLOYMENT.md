# Deployment Guide

This document provides instructions for deploying the Raster to SVG Converter to production.

## Table of Contents

- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Variables](#environment-variables)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Monitoring Setup](#monitoring-setup)
- [Backup and Recovery](#backup-and-recovery)
- [Troubleshooting](#troubleshooting)

## Docker Deployment

### Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- 4GB RAM minimum (8GB recommended)
- 20GB disk space

### Quick Start

1. Clone the repository:
```bash
git clone <repository-url>
cd raster-to-svg
```

2. Create environment file:
```bash
cp backend/.env.example backend/.env
# Edit backend/.env with production settings
```

3. Start services:
```bash
docker-compose up -d
```

4. Verify services:
```bash
docker-compose ps
```

### Production Configuration

Create a `docker-compose.prod.yml` for production:

```yaml
version: '3.8'

services:
  redis:
    restart: always
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  api:
    restart: always
    environment:
      - DEBUG=False
      - LOG_LEVEL=WARNING
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '1'
          memory: 1G

  worker:
    restart: always
    environment:
      - DEBUG=False
      - LOG_LEVEL=WARNING
    deploy:
      replicas: 4
      resources:
        limits:
          cpus: '2'
          memory: 2G

  frontend:
    restart: always
    deploy:
      replicas: 2
```

Deploy with:
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes 1.24+
- kubectl configured
- Ingress controller (nginx recommended)
- cert-manager (for SSL)

### Deployment Steps

1. Create namespace:
```bash
kubectl apply -f k8s/namespace.yaml
```

2. Deploy Redis:
```bash
kubectl apply -f k8s/redis-deployment.yaml
```

3. Deploy API:
```bash
kubectl apply -f k8s/api-deployment.yaml
```

4. Deploy Workers:
```bash
kubectl apply -f k8s/worker-deployment.yaml
```

5. Deploy Frontend:
```bash
kubectl apply -f k8s/frontend-deployment.yaml
```

6. Configure Ingress:
```bash
kubectl apply -f k8s/ingress.yaml
```

### Scaling

Scale workers based on queue length:
```bash
kubectl scale deployment worker --replicas=5 -n raster-svg
```

## Environment Variables

### Required Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REDIS_URL` | Redis connection URL | `redis://localhost:6379` |
| `CELERY_BROKER_URL` | Celery broker URL | `redis://localhost:6379/0` |
| `CELERY_RESULT_BACKEND` | Celery result backend | `redis://localhost:6379/1` |
| `API_HOST` | API bind address | `0.0.0.0` |
| `API_PORT` | API port | `8000` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `False` |
| `LOG_LEVEL` | Logging level | `INFO` |
| `MAX_IMAGE_SIZE` | Max upload size in bytes | `52428800` |
| `CLEANUP_AGE_DAYS` | File retention in days | `30` |
| `CONVERSION_TIMEOUT` | Conversion timeout in seconds | `300` |

## SSL/TLS Configuration

### Using Let's Encrypt with cert-manager

1. Install cert-manager:
```bash
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml
```

2. Create ClusterIssuer:
```yaml
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: your-email@example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
```

3. Apply:
```bash
kubectl apply -f cluster-issuer.yaml
```

### Using Custom Certificates

Create TLS secret:
```bash
kubectl create secret tls raster-svg-tls \
  --cert=path/to/cert.crt \
  --key=path/to/cert.key \
  -n raster-svg
```

## Monitoring Setup

### Enable Monitoring Stack

```bash
docker-compose --profile monitoring up -d
```

Access:
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3001 (admin/admin)
- Flower: http://localhost:5555

### Key Metrics

| Metric | Description | Alert Threshold |
|--------|-------------|-----------------|
| `celery_queue_length` | Pending tasks | > 100 |
| `conversion_duration_seconds` | Conversion time | > 30s |
| `api_request_duration` | API latency | > 2s |
| `disk_free_percent` | Disk space | < 10% |

### Grafana Dashboard

Import dashboard ID `1860` for node monitoring.

## Backup and Recovery

### Redis Backup

Enable AOF persistence (already configured in docker-compose.prod.yml).

Manual backup:
```bash
docker exec raster-svg-redis redis-cli BGSAVE
docker cp raster-svg-redis:/data/dump.rdb ./backup/redis-$(date +%Y%m%d).rdb
```

### File Storage Backup

Backup storage directory:
```bash
tar -czf backup/storage-$(date +%Y%m%d).tar.gz ./storage
```

### Automated Backups

Add to crontab:
```bash
0 2 * * * /path/to/backup-script.sh
```

## Troubleshooting

### High Memory Usage

1. Check worker memory:
```bash
docker stats raster-svg-worker
```

2. Scale down workers if needed:
```bash
kubectl scale deployment worker --replicas=2 -n raster-svg
```

### Queue Backlog

1. Check queue length:
```bash
docker exec raster-svg-redis redis-cli LLEN celery
```

2. Scale up workers:
```bash
kubectl scale deployment worker --replicas=10 -n raster-svg
```

### Failed Conversions

1. Check worker logs:
```bash
docker logs raster-svg-worker --tail 100
```

2. Check job status in Redis:
```bash
docker exec raster-svg-redis redis-cli HGETALL job:<job_id>
```

### Database Connection Issues

1. Verify Redis connectivity:
```bash
docker exec raster-svg-api python -c "import redis; r = redis.from_url('redis://redis:6379'); print(r.ping())"
```

## Performance Tuning

### Worker Concurrency

Adjust based on CPU cores:
```python
# In Dockerfile.worker
CMD ["celery", "-A", "app.workers.celery", "worker", "--concurrency=4"]
```

### Redis Optimization

Add to redis.conf:
```
maxmemory 512mb
maxmemory-policy allkeys-lru
```

### API Workers

For high traffic, increase uvicorn workers:
```bash
uvicorn app.main:app --workers 4
```

## Security Checklist

- [ ] Use strong passwords for Redis
- [ ] Enable SSL/TLS
- [ ] Run containers as non-root
- [ ] Keep images updated
- [ ] Use network policies in Kubernetes
- [ ] Enable audit logging
- [ ] Regular security scans
- [ ] Backup encryption

## Rollback Procedure

1. List available images:
```bash
docker images | grep raster-to-svg
```

2. Rollback to previous version:
```bash
docker-compose pull
docker-compose up -d
```

3. For Kubernetes:
```bash
kubectl rollout undo deployment/api -n raster-svg
```
