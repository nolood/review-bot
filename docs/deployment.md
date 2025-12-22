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

### 3. Kubernetes Deployment

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

### 4. Manual/Local Deployment

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