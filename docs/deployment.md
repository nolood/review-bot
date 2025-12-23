# Deployment Guide

## Overview

This guide covers deploying the GLM Code Review Bot in various environments, from development setup to production deployment. It includes best practices, security considerations, and monitoring recommendations.

## Deployment Options

### 1. GitLab CI/CD (Recommended)

The most common and secure deployment is through GitLab's built-in CI/CD.

#### Prerequisites
- GitLab Runner configured
- CI/CD variables set for secrets
- `.gitlab-ci.yml` in project root

#### Configuration
```yaml
# .gitlab-ci.yml
stages:
  - validate
  - test
  - review

variables:
  PYTHON_VERSION: "3.11"
  TIMEOUT: "600"

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

code_review:
  stage: review
  image: python:${PYTHON_VERSION}
  before_script:
    - python -m venv venv
    - source venv/bin/activate
    - pip install --upgrade pip
    - pip install -r requirements.txt
  script:
    - python review_bot.py
  artifacts:
    paths:
      - review_logs/
    expire_in: 1 week
    when: always
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: manual
  environment:
    name: review/${CI_MERGE_REQUEST_IID}
    url: $CI_PROJECT_URL/-/merge_requests/$CI_MERGE_REQUEST_IID
```

#### Step-by-Step Deployment

1. **Set CI/CD Variables**:
   - Go to Project → Settings → CI/CD → Variables
   - Add `GITLAB_TOKEN` with `api`, `read_repository`, `read_api` scopes
   - Add `GLM_API_KEY` from GLM Platform
   - Mark as "Protected" if needed

2. **Add Pipeline Configuration**:
   - Create `.gitlab-ci.yml` in project root
   - Customize based on project needs
   - Test with dry-run first

3. **Verify Integration**:
   - Create test merge request
   - Manually trigger review job
   - Check for comments on MR

4. **Enable Automatic Reviews** (optional):
   ```yaml
   rules:
     - if: $CI_PIPELINE_SOURCE == "merge_request_event"
       # when: manual  # Remove for automatic
   ```

### 2. Docker Deployment

For self-hosted deployment or custom infrastructure.

#### Building the Image

```bash
# Clone repository
git clone https://gitlab.com/your-org/review-bot.git
cd review-bot

# Build image
docker build -t review-bot:latest .

# Tag for registry
docker tag review-bot:latest registry.example.com/review-bot:latest
```

#### Running with Docker

```bash
# Create environment file
cat > .env << EOF
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GLM_API_KEY=your-glm-api-key
LOG_LEVEL=INFO
EOF

# Run container
docker run --rm \
  --env-file .env \
  -v /path/to/logs:/app/logs \
  review-bot:latest
```

#### Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  review-bot:
    build: .
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
      - ./config:/app/config
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "-c", "import sys; sys.exit(0)"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 512M
          cpus: '0.5'
        reservations:
          memory: 256M
          cpus: '0.25'

volumes:
  logs:
    driver: local
```

### 3. Webhook Server Deployment

For real-time review triggering via GitLab webhooks (alternative to CI/CD).

**Key Differences from CI/CD:**
- Server runs continuously, listens for webhook events
- Reviews start immediately when MRs are created/updated
- No pipeline overhead or job scheduling delays
- Requires public-facing URL for GitLab to reach

#### Prerequisites
- Public or accessible domain for webhook endpoint
- Valid HTTPS certificate (strongly recommended)
- Persistent service (not terminating)
- Firewall rules to allow GitLab to reach your endpoint

#### Docker Webhook Server

```bash
# Run webhook server
docker run -d \
  --name review-bot-webhook \
  -p 8000:8000 \
  -p 8080:8080 \
  -e GITLAB_TOKEN="your_token" \
  -e GLM_API_KEY="your_key" \
  -e WEBHOOK_ENABLED="true" \
  -e WEBHOOK_SECRET="$(openssl rand -hex 32)" \
  -e WEBHOOK_VALIDATE_SIGNATURE="true" \
  -e SERVER_HOST="0.0.0.0" \
  -e SERVER_PORT="8000" \
  review-bot:latest
```

#### Docker Compose for Webhook Server

```yaml
version: '3.8'

services:
  review-bot-webhook:
    image: review-bot:latest
    container_name: review-bot-webhook
    restart: unless-stopped
    ports:
      - "8000:8000"    # Main webhook endpoint
      - "8080:8080"    # Monitoring/metrics
    environment:
      # GitLab
      GITLAB_TOKEN: ${GITLAB_TOKEN}
      GITLAB_API_URL: https://gitlab.com/api/v4

      # GLM
      GLM_API_KEY: ${GLM_API_KEY}
      GLM_API_URL: https://api.z.ai/api/paas/v4/chat/completions

      # Webhook Configuration
      WEBHOOK_ENABLED: "true"
      WEBHOOK_SECRET: ${WEBHOOK_SECRET}
      WEBHOOK_VALIDATE_SIGNATURE: "true"
      WEBHOOK_SKIP_DRAFT: "true"
      WEBHOOK_SKIP_WIP: "true"
      WEBHOOK_TRIGGER_ACTIONS: "open,update,reopen"

      # Server
      SERVER_HOST: "0.0.0.0"
      SERVER_PORT: "8000"
      LOG_LEVEL: "INFO"

      # Processing
      MAX_CONCURRENT_REVIEWS: "5"
      REVIEW_TIMEOUT_SECONDS: "300"

      # Deduplication
      DEDUPLICATION_STRATEGY: "DELETE_SUMMARY_ONLY"

    volumes:
      # Persistent data for commit tracking
      - webhook-data:/data
      - ./logs:/app/logs

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  webhook-data:
    driver: local
```

#### Webhook with Reverse Proxy (NGINX)

For public accessibility with TLS:

```nginx
# /etc/nginx/sites-available/review-bot-webhook
upstream review_bot_backend {
    server 127.0.0.1:8000;
    keepalive 32;
}

server {
    listen 80;
    server_name review-bot.example.com;

    location / {
        return 301 https://$server_name$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name review-bot.example.com;

    # SSL certificates (use Let's Encrypt)
    ssl_certificate /etc/letsencrypt/live/review-bot.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/review-bot.example.com/privkey.pem;

    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;

    # Webhook endpoint
    location /webhook/gitlab {
        proxy_pass http://review_bot_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_buffering off;
        proxy_read_timeout 300s;
        proxy_connect_timeout 30s;
    }

    # Health check
    location /health {
        proxy_pass http://review_bot_backend;
        access_log off;
    }

    # API endpoints
    location /api {
        proxy_pass http://review_bot_backend;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

Enable and restart:
```bash
sudo ln -s /etc/nginx/sites-available/review-bot-webhook /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Configuration for GitLab

In your GitLab project:

1. Settings → Integrations → Webhooks
2. URL: `https://review-bot.example.com/webhook/gitlab`
3. Secret token: Use value from `WEBHOOK_SECRET` environment variable
4. Trigger: Merge request events
5. SSL verification: Enabled

See [Webhook Setup Guide](webhook_setup.md) for detailed configuration.

### 4. Kubernetes Deployment

For scalable, managed deployment.

#### Deployment Manifest

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: review-bot
  labels:
    app: review-bot
spec:
  replicas: 1
  selector:
    matchLabels:
      app: review-bot
  template:
    metadata:
      labels:
        app: review-bot
    spec:
      containers:
      - name: review-bot
        image: review-bot:latest
        ports:
        - containerPort: 8080
        envFrom:
        - secretRef:
            name: review-bot-secrets
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          exec:
            command:
            - python
            - -c
            - "import sys; sys.exit(0)"
          initialDelaySeconds: 5
          periodSeconds: 5
```

#### Service Configuration

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: review-bot-service
spec:
  selector:
    app: review-bot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: ClusterIP
```

#### Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: review-bot-secrets
type: Opaque
data:
  GITLAB_TOKEN: <base64-encoded-token>
  GLM_API_KEY: <base64-encoded-key>
```

### 5. Manual/Local Deployment

For development or testing.

#### System Setup

```bash
# System requirements
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Create user
sudo useradd -m -s /bin/bash reviewbot
sudo su - reviewbot

# Clone and setup
git clone https://gitlab.com/your-org/review-bot.git
cd review-bot
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

#### Service Configuration

```bash
# Create systemd service
sudo tee /etc/systemd/system/review-bot.service > /dev/null <<EOF
[Unit]
Description=GLM Code Review Bot
After=network.target

[Service]
Type=oneshot
User=reviewbot
Group=reviewbot
WorkingDirectory=/home/reviewbot/review-bot
Environment=PYTHONPATH=/home/reviewbot/review-bot/src
EnvironmentFile=/home/reviewbot/.env
ExecStart=/home/reviewbot/review-bot/venv/bin/python review_bot.py
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable review-bot
```

## Configuration Management

### Environment-Specific Configs

#### Development
```bash
# config/development.env
LOG_LEVEL=DEBUG
API_REQUEST_DELAY=0.1
MAX_DIFF_SIZE=25000
ENABLE_INLINE_COMMENTS=false
```

#### Staging
```bash
# config/staging.env
LOG_LEVEL=INFO
API_REQUEST_DELAY=0.5
MAX_DIFF_SIZE=50000
DRY_RUN=true
```

#### Production
```bash
# config/production.env
LOG_LEVEL=WARNING
API_REQUEST_DELAY=1.0
MAX_DIFF_SIZE=75000
ENABLE_SECURITY_REVIEW=true
MIN_SEVERITY_LEVEL=medium
```

### Using Multiple Configs

```bash
# Load appropriate config based on environment
ENVIRONMENT=${ENVIRONMENT:-production}
cp config/${ENVIRONMENT}.env .env
export $(cat .env | xargs)

# Run with loaded config
python review_bot.py
```

## Security Configuration

### Secrets Management

#### HashiCorp Vault Integration

```python
# src/config/vault.py
import hvac

class VaultConfig:
    def __init__(self):
        self.client = hvac.Client(url='https://vault.company.com')
        
    def get_secret(self, path: str) -> dict:
        return self.client.read(f'secret/data/{path}')['data']['data']

# Usage in settings
vault = VaultConfig()
settings.gitlab_token = vault.get_secret('gitlab/token')['value']
```

#### Kubernetes Secrets

```yaml
# Create sealed secrets
kubeseal --format yaml < k8s/secrets.yaml > k8s/sealed-secrets.yaml

# Apply sealed secrets
kubectl apply -f k8s/sealed-secrets.yaml
```

#### AWS Secrets Manager

```python
# src/config/aws_secrets.py
import boto3
import json

def get_secret(secret_name: str) -> dict:
    client = boto3.client('secretsmanager')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])
```

### Network Security

#### TLS/SSL Configuration

```bash
# Enforce HTTPS
export GITLAB_API_URL="https://gitlab.company.com/api/v4"
export GLM_API_URL="https://api.z.ai/api/paas/v4/chat/completions"

# Certificate verification
export SSL_VERIFY=true
export CA_CERT_PATH="/etc/ssl/certs/ca-bundle.crt"
```

#### Network Policies (Kubernetes)

```yaml
# k8s/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: review-bot-netpol
spec:
  podSelector:
    matchLabels:
      app: review-bot
  policyTypes:
  - Egress
  egress:
  - to:
    - namespaceSelector:
        matchLabels:
          name: gitlab
    ports:
    - protocol: TCP
      port: 443
  - to: []
    ports:
    - protocol: TCP
      port: 443
```

## Monitoring and Observability

### Logging Configuration

#### Structured JSON Logging

```bash
# Enable JSON logging for production
export LOG_FORMAT=json
export LOG_LEVEL=INFO
export LOG_FILE=/var/log/review-bot/app.log

# With log rotation
export LOG_MAX_SIZE=100MB
export LOG_BACKUP_COUNT=5
```

#### Log Aggregation (ELK Stack)

```yaml
# k8s/filebeat.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: filebeat-config
data:
  filebeat.yml: |
    filebeat.inputs:
    - type: log
      paths:
        - /var/log/review-bot/*.log
      json.keys_under_root: true
    output.elasticsearch:
      hosts: ["elasticsearch:9200"]
      index: "review-bot-%{+yyyy.MM.dd}"
```

### Metrics Collection

#### Prometheus Metrics

```python
# src/metrics.py
from prometheus_client import Counter, Histogram, generate_latest

# Define metrics
request_counter = Counter('bot_requests_total', 'Total requests', ['endpoint', 'status'])
processing_time = Histogram('bot_processing_seconds', 'Processing time')

# Export metrics endpoint
def metrics_handler():
    return generate_latest()
```

#### Grafana Dashboard

```json
{
  "dashboard": {
    "title": "Review Bot Metrics",
    "panels": [
      {
        "title": "Request Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(bot_requests_total[5m])",
            "legendFormat": "{{endpoint}}"
          }
        ]
      },
      {
        "title": "Processing Time",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(bot_processing_seconds_bucket[5m]))",
            "legendFormat": "95th percentile"
          }
        ]
      }
    ]
  }
}
```

### Alerting

#### Alertmanager Configuration

```yaml
# alertmanager.yml
global:
  smtp_smarthost: 'smtp.company.com:587'
  smtp_from: 'alerts@company.com'

route:
  group_by: ['alertname']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'web.hook'

receivers:
- name: 'web.hook'
  email_configs:
  - to: 'team@company.com'
    subject: '[Alert] Review Bot: {{ .GroupLabels.alertname }}'
    body: |
      {{ range .Alerts }}
      Alert: {{ .Annotations.summary }}
      Description: {{ .Annotations.description }}
      {{ end }}
```

## Scaling and Performance

### Horizontal Scaling

#### GitLab Runner Autoscaling

```yaml
# runners-autoscaler.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: gitlab-runner-config
data:
  config.toml: |
    [[runners]]
      executor = "kubernetes"
      [runners.kubernetes]
        [[runners.kubernetes.pods_per_job]]
          memory = "512Mi"
          cpu = "500m"
        [runners.kubernetes]
          [[runners.kubernetes.pods_per_job]]
            memory = "256Mi"
            cpu = "250m"
```

#### Container Autoscaling

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: review-bot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: review-bot
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

### Performance Optimization

#### Resource Tuning

```yaml
# Production resource recommendations
resources:
  requests:
    memory: "512Mi"
    cpu: "500m"
  limits:
    memory: "1Gi"
    cpu: "1000m"
```

#### Caching Strategy

```python
# src/cache.py
from functools import lru_cache
import redis

@lru_cache(maxsize=128)
def estimate_tokens(content: str) -> int:
    """Cache token estimation results."""
    # Implementation
    pass

class RedisCache:
    def __init__(self):
        self.redis = redis.Redis(host='redis', port=6379)
    
    def get_diff_cache(self, diff_hash: str) -> str:
        """Retrieve cached diff analysis."""
        return self.redis.get(f"diff:{diff_hash}")
```

## Backup and Recovery

### Data Backup

#### Configuration Backup

```bash
# Backup configurations
tar -czf backup/config-$(date +%Y%m%d).tar.gz config/ .env

# GitLab CI/CD backup
gitlab-backup \
  --url https://gitlab.company.com \
  --token $BACKUP_TOKEN \
  --output backup/gitlab-$(date +%Y%m%d).tar
```

#### Log Backup

```bash
# Rotate and backup logs
logrotate -f /etc/logrotate.d/review-bot

# Archive old logs
find /var/log/review-bot -name "*.log" -mtime +30 -exec gzip {} \;
find /var/log/review-bot -name "*.log.gz" -mtime +90 -delete
```

### Disaster Recovery

#### Recovery Procedures

```bash
# 1. Restore configuration
tar -xzf backup/config-20231221.tar.gz -C /

# 2. Restart services
sudo systemctl restart review-bot
sudo kubectl rollout restart deployment/review-bot

# 3. Verify functionality
python review_bot.py --validate-only
```

#### High Availability Setup

```yaml
# Multi-zone deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: review-bot-ha
spec:
  replicas: 3
  template:
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: app
                operator: In
                values:
                - review-bot
            topologyKey: "kubernetes.io/hostname"
```

## Troubleshooting Deployment

### Common Issues

1. **Authentication Failures**
   ```bash
   # Test tokens
   curl -H "Authorization: Bearer $GITLAB_TOKEN" \
        "$GITLAB_API_URL/projects"
   ```

2. **Network Connectivity**
   ```bash
   # Test API reachability
   nc -zv gitlab.com 443
   nc -zv api.z.ai 443
   ```

3. **Resource Constraints**
   ```bash
   # Check resource usage
   kubectl top pods -l app=review-bot
   kubectl describe pod -l app=review-bot
   ```

4. **Configuration Issues**
   ```bash
   # Validate configuration
   python review_bot.py --validate-only
   ```

### Debugging Production Issues

#### Enabling Debug Mode

```bash
# Temporary debug configuration
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json
export LOG_FILE=/tmp/debug.log

# Restart with debug
kubectl set env deployment/review-bot LOG_LEVEL=DEBUG
kubectl rollout restart deployment/review-bot
```

#### Analyzing Logs

```bash
# Search for errors
kubectl logs -l app=review-bot | grep ERROR

# Follow logs in real-time
kubectl logs -f -l app=review-bot

# Export logs for analysis
kubectl logs -l app=review-bot > review-bot-debug.log
```

This deployment guide covers all major deployment scenarios and provides production-ready configurations for the GLM Code Review Bot.

## Production Readiness Checklist

### Pre-Deployment Requirements

Before deploying to production, ensure the following are completed:

#### Security Configuration
- [ ] All API tokens are properly secured and rotated
- [ ] SSL/TLS certificates are installed and valid
- [ ] Network policies are configured
- [ ] Access controls are implemented
- [ ] Secrets management is configured (Vault/AWS Secrets Manager)
- [ ] Security scanning passes (refer to `security.md`)

#### Environment Setup
- [ ] Production environment variables are configured
- [ ] Monitoring and alerting are set up
- [ ] Backup procedures are documented and tested
- [ ] Resource limits are properly sized
- [ ] Health checks are implemented
- [ ] Logging is configured for production

#### CI/CD Pipeline
- [ ] `.gitlab-ci.yml` is configured for production
- [ ] Docker images are built and pushed to registry
- [ ] Blue-green deployment strategy is tested
- [ ] Rollback procedures are documented
- [ ] Integration tests pass in staging

### Production Deployment Process

#### 1. Environment Preparation

```bash
# Create production environment file
cat > .env.production << EOF
# Core Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/review-bot/app.log

# API Configuration
GITLAB_API_URL=https://gitlab.company.com/api/v4
GLM_API_URL=https://api.z.ai/api/paas/v4/chat/completions

# Processing Configuration
MAX_DIFF_SIZE=75000
MAX_FILES_PER_COMMENT=15
ENABLE_INLINE_COMMENTS=true
MIN_SEVERITY_LEVEL=medium

# Performance Tuning
API_REQUEST_DELAY=1.0
MAX_PARALLEL_REQUESTS=2
TIMEOUT_SECONDS=900
GLM_TIMEOUT=120

# Security
ENABLE_SECURITY_REVIEW=true
REDACT_SENSITIVE_DATA=true
SSL_VERIFY=true

# Monitoring
ENABLE_METRICS=true
METRICS_PORT=9090
HEALTH_CHECK_INTERVAL=30s
EOF
```

#### 2. Production Deployment Commands

```bash
# Deploy to production using CI/CD
git push origin main  # Triggers production deployment pipeline

# Or deploy manually
./scripts/deploy.sh production latest

# Verify deployment
./scripts/health-check.sh review-bot
```

#### 3. Post-Deployment Verification

```bash
# Check service status
docker ps | grep review-bot

# Check logs for errors
docker logs review-bot --tail=100 | grep ERROR

# Verify health endpoint
curl -f https://review-bot.example.com/health

# Check metrics endpoint
curl https://review-bot.example.com/metrics
```

## Environment-Specific Deployments

### Development Environment

**Purpose**: Local development and testing
**Configuration**: `config/development.env`
**Resources**: Minimal (1 CPU, 512MB RAM)
**Monitoring**: Basic logging only

```bash
# Quick development setup
docker-compose -f docker-compose.yml up -d
docker-compose -f docker-compose.yml logs -f review-bot
```

### Staging Environment

**Purpose**: Pre-production testing
**Configuration**: `config/staging.env`
**Resources**: Medium (2 CPUs, 1GB RAM)
**Monitoring**: Full logging + basic metrics

```bash
# Deploy to staging
./scripts/deploy.sh staging latest

# Run integration tests against staging
python -m pytest tests/integration/ --base-url=https://review-bot-staging.example.com
```

### Production Environment

**Purpose**: Live service
**Configuration**: `config/production.env`
**Resources**: High (4 CPUs, 2GB RAM per replica)
**Monitoring**: Full observability stack

```bash
# Production deployment (blue-green)
./scripts/deploy.sh production latest

# Scale horizontally
docker-compose -f docker-compose.prod.yml up -d --scale review-bot=3
```

## High Availability Deployment

### Multi-Region Setup

```yaml
# k8s/multi-region-deployment.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: review-bot-config
data:
  REGION_PRIMARY: "us-east-1"
  REGION_SECONDARY: "us-west-2"
  ENABLE_CROSS_REGION_SYNC: "true"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: review-bot-primary
  labels:
    app: review-bot
    region: primary
spec:
  replicas: 3
  selector:
    matchLabels:
      app: review-bot
      region: primary
  template:
    metadata:
      labels:
        app: review-bot
        region: primary
    spec:
      affinity:
        podAntiAffinity:
          requiredDuringSchedulingIgnoredDuringExecution:
          - labelSelector:
              matchExpressions:
              - key: region
                operator: In
                values:
                - primary
            topologyKey: "kubernetes.io/hostname"
      containers:
      - name: review-bot
        image: review-bot:latest
        env:
        - name: REGION
          value: "primary"
        - name: IS_PRIMARY
          value: "true"
```

### Database Replication (if needed)

```yaml
# PostgreSQL for review queue persistence
apiVersion: postgresql.cnpg.io/v1
kind: Cluster
metadata:
  name: review-bot-db
spec:
  instances: 3
  primaryUpdateStrategy: unsupervised
  
  postgresql:
    parameters:
      max_connections: "200"
      shared_buffers: "256MB"
      effective_cache_size: "1GB"
      
  bootstrap:
    initdb:
      database: reviewbot
      owner: reviewbot
      secret:
        name: review-bot-db-creds
        
  storage:
    size: 100Gi
    storageClass: fast-ssd
    
  monitoring:
    enabled: true
```

## Disaster Recovery

### Backup Strategy

```bash
#!/bin/bash
# scripts/backup.sh

BACKUP_DIR="/opt/backups/review-bot"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Backup configurations
tar -czf "$BACKUP_DIR/config-$DATE.tar.gz" config/ .env

# Backup Docker volumes
docker run --rm -v review-bot_data:/data -v "$BACKUP_DIR":/backup \
  alpine tar czf "/backup/data-$DATE.tar.gz" -C /data .

# Backup database (if using PostgreSQL)
kubectl exec -n review-bot deployment/review-bot-db -- \
  pg_dump -U reviewbot reviewbot > "$BACKUP_DIR/db-$DATE.sql"

# Upload to cloud storage (AWS S3 example)
aws s3 sync "$BACKUP_DIR" s3://review-bot-backups/$DATE/

# Cleanup old backups (keep 30 days)
find "$BACKUP_DIR" -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

### Recovery Procedures

```bash
#!/bin/bash
# scripts/recover.sh

BACKUP_DATE=$1
BACKUP_DIR="/opt/backups/review-bot"

if [ -z "$BACKUP_DATE" ]; then
    echo "Usage: $0 <backup_date>"
    exit 1
fi

# Stop current deployment
docker-compose -f docker-compose.prod.yml down

# Restore configurations
tar -xzf "$BACKUP_DIR/config-$BACKUP_DATE.tar.gz"

# Restore data volumes
docker run --rm -v review-bot_data:/data -v "$BACKUP_DIR":/backup \
  alpine tar xzf "/backup/data-$BACKUP_DATE.tar.gz" -C /data

# Restore database (if needed)
kubectl exec -i -n review-bot deployment/review-bot-db -- \
  psql -U reviewbot -c "DROP DATABASE IF EXISTS reviewbot;"
kubectl exec -i -n review-bot deployment/review-bot-db -- \
  psql -U reviewbot -c "CREATE DATABASE reviewbot;"
kubectl exec -i -n review-bot deployment/review-bot-db -- \
  psql -U reviewbot reviewbot < "$BACKUP_DIR/db-$BACKUP_DATE.sql"

# Restart services
docker-compose -f docker-compose.prod.yml up -d

# Verify recovery
./scripts/health-check.sh review-bot

echo "Recovery completed from backup: $BACKUP_DATE"
```

## Performance Optimization

### Resource Tuning Guidelines

#### CPU Allocation
- **Small deployments**: 0.5 - 1 CPU cores
- **Medium deployments**: 2 - 4 CPU cores  
- **Large deployments**: 4 - 8 CPU cores

#### Memory Allocation
- **Minimum**: 512MB RAM
- **Recommended**: 1-2GB RAM per instance
- **Large diffs**: 4GB+ RAM for processing

#### Scaling Thresholds
```yaml
# Horizontal Pod Autoscaler configuration
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: review-bot-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: review-bot
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  behavior:
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 15
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 10
        periodSeconds: 60
```

### Caching Strategy

```python
# Redis configuration for production
REDIS_CONFIG = {
    'host': 'redis-cluster.review-bot.svc.cluster.local',
    'port': 6379,
    'db': 0,
    'password': os.getenv('REDIS_PASSWORD'),
    'ssl': True,
    'ssl_cert_reqs': 'required',
    'socket_timeout': 5,
    'socket_connect_timeout': 5,
    'retry_on_timeout': True,
    'health_check_interval': 30
}

# Cache settings
CACHE_SETTINGS = {
    'diff_analysis_ttl': 3600,  # 1 hour
    'token_estimation_ttl': 86400,  # 24 hours
    'file_metadata_ttl': 1800,  # 30 minutes
    'rate_limit_ttl': 60,  # 1 minute
}
```

## Migration Guide

### Version Upgrade Process

1. **Pre-upgrade Checks**
```bash
# Check current version
docker inspect review-bot | grep -i version

# Run compatibility tests
python -m pytest tests/upgrade/ -v

# Backup current deployment
./scripts/backup.sh
```

2. **Rolling Upgrade**
```bash
# Update to new version
docker pull review-bot:v2.1.0

# Rolling update with zero downtime
docker-compose -f docker-compose.prod.yml up -d --no-deps review-bot

# Monitor rollout
watch docker ps | grep review-bot
```

3. **Post-upgrade Validation**
```bash
# Verify new version
curl https://review-bot.example.com/health

# Run smoke tests
python -m pytest tests/smoke/ --base-url=https://review-bot.example.com

# Monitor for 15 minutes
./scripts/monitor-deployment.sh 900
```

### Configuration Migration

```bash
#!/bin/bash
# scripts/migrate-config.sh

OLD_VERSION=$1
NEW_VERSION=$2

echo "Migrating configuration from $OLD_VERSION to $NEW_VERSION"

# Backup current config
cp .env .env.backup.$OLD_VERSION

# Update configuration template
python scripts/config-migrator.py \
  --from-version $OLD_VERSION \
  --to-version $NEW_VERSION \
  --config-file .env

# Validate new configuration
python review_bot.py --validate-only

echo "Configuration migration completed"
```

This enhanced deployment guide provides comprehensive coverage of production deployment scenarios, high availability setup, disaster recovery procedures, and performance optimization strategies for the GLM Code Review Bot.