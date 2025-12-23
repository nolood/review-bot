# Docker Compose Monitoring Stack

This document describes the complete monitoring stack implemented in the Docker Compose configurations.

## Overview

The monitoring stack provides comprehensive observability for the GLM Code Review Bot with the following components:

- **Prometheus**: Metrics collection and storage
- **Grafana**: Data visualization and dashboards
- **Node Exporter**: System metrics
- **cAdvisor**: Container metrics
- **AlertManager**: Alerting and notifications
- **Traefik**: Reverse proxy with metrics

## Services

### Application Services

#### review-bot
Main application service with monitoring enabled:
- **Metrics Port**: 8000 (Prometheus metrics)
- **Health Port**: 8001 (Health checks)
- **Environment Variables**:
  - `METRICS_ENABLED`: Enable metrics collection
  - `METRICS_PORT`: Metrics port (default: 8000)
  - `HEALTH_CHECK_ENABLED`: Enable health checks
  - `HEALTH_CHECK_PORT`: Health check port (default: 8001)

#### review-bot-new / review-bot-old
Blue-green deployment variants with separate monitoring ports.

### Monitoring Services

#### Prometheus
- **Port**: 9090
- **Data Retention**: 15 days (dev) / 30 days (prod)
- **Configuration**: `./monitoring/prometheus.yml`
- **Alert Rules**: `./monitoring/rules/alerting.yml`
- **Features**:
  - Administrative API enabled
  - Lifecycle management enabled
  - Alert rule evaluation

#### Grafana
- **Port**: 3000
- **Admin User**: Configurable via `GRAFANA_USER`
- **Admin Password**: Configurable via `GRAFANA_PASSWORD`
- **Plugins**: Pie chart panel
- **Security**: Cookie security enabled, Samesite=strict

#### Node Exporter
- **Port**: 9100
- **Metrics**: System resources (CPU, memory, disk, network)
- **Security**: Read-only filesystem access

#### cAdvisor
- **Port**: 8080
- **Metrics**: Container performance and resource usage
- **Privileged**: Required for container metrics
- **Storage Duration**: 2 minutes

#### AlertManager
- **Port**: 9093
- **Configuration**: `./monitoring/alertmanager.yml`
- **Templates**: `./monitoring/alertmanager_templates/`
- **Features**:
  - SMTP notifications
  - Webhook notifications
  - Alert clustering
  - Inhibition rules

#### Traefik (Production Only)
- **Ports**: 80, 443, 8082 (metrics)
- **Features**:
  - Automatic HTTPS
  - Metrics collection
  - Dashboard
  - Load balancing
  - Health checks

## Network Configuration

### Development
- **Network**: `review-bot-network`
- **Subnet**: `172.20.0.0/16`

### Production
- **Network**: `review-bot-prod`
- **Subnet**: `172.21.0.0/16`

## Volumes

### Application Volumes
- `logs`: Application logs
- `review_logs`: Review-specific logs
- `config`: Configuration files

### Monitoring Volumes
- `prometheus_data`: Prometheus time-series data
- `grafana_data`: Grafana dashboards and user data
- `alertmanager_data`: AlertManager configuration and state

## Health Checks

All services include comprehensive health checks:

### Application Health Checks
- **Basic**: Python import test
- **Enhanced**: HTTP endpoint test
- **Interval**: 30 seconds
- **Timeout**: 10 seconds
- **Retries**: 3
- **Start Period**: 40-60 seconds

### Monitoring Service Health Checks
- **Prometheus**: `GET /-/healthy`
- **Grafana**: `GET /api/health`
- **Node Exporter**: `GET /metrics`
- **cAdvisor**: `GET /healthz`
- **AlertManager**: `GET /-/healthy`

## Metrics Endpoints

### Application Metrics
- **Prometheus Format**: `GET /metrics` (port 8000)
- **Health**: `GET /health` (port 8001)
- **System Info**: `GET /system-info`

### Service Metrics
- **Prometheus**: `http://localhost:9090/metrics`
- **Node Exporter**: `http://localhost:9100/metrics`
- **cAdvisor**: `http://localhost:8080/metrics`
- **AlertManager**: `http://localhost:9093/metrics`

## Alerting Configuration

### Alert Types
1. **Application Alerts**:
   - Review Bot down
   - High memory usage (>90%)
   - High CPU usage (>80%)
   - High error rate (>10%)

2. **System Alerts**:
   - High disk usage (>85%)
   - High memory usage (>90%)
   - High CPU usage (>85%)

3. **Container Alerts**:
   - Container down
   - Container restarting frequently

4. **Monitoring Alerts**:
   - Prometheus down
   - Grafana down
   - AlertManager down

### Alert Severity
- **Critical**: Immediate attention required
- **Warning**: Attention needed soon

### Notification Channels
- **Email**: SMTP notifications
- **Webhooks**: HTTP POST notifications
- **Slack**: Integration via webhooks

## Environment Variables

### Application Variables
```bash
# Monitoring Configuration
METRICS_ENABLED=true
METRICS_PORT=8000
HEALTH_CHECK_ENABLED=true
HEALTH_CHECK_PORT=8001

# Application Configuration
LOG_LEVEL=INFO
MAX_FILE_SIZE=1000
TOKEN_LIMIT=8000
REVIEW_TYPE=comprehensive
```

### Monitoring Variables
```bash
# Grafana
GRAFANA_USER=admin
GRAFANA_PASSWORD=secure_password

# AlertManager SMTP
SMTP_HOST=smtp.example.com:587
SMTP_FROM=alerts@example.com
SMTP_USER=alerts@example.com
SMTP_PASSWORD=smtp_password

# Notification Emails
DEFAULT_EMAIL=admin@example.com
CRITICAL_EMAIL=admin@example.com
WARNING_EMAIL=dev-team@example.com
REVIEW_BOT_EMAIL=dev-team@example.com

# Webhooks
WEBHOOK_URL=https://hooks.slack.com/services/xxx
```

## Usage

### Development
```bash
# Start all services including monitoring
docker-compose up -d

# Start only monitoring services
docker-compose up -d prometheus grafana node-exporter cadvisor alertmanager

# View logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

### Production
```bash
# Start production stack with monitoring
docker-compose -f docker-compose.prod.yml up -d

# Scale review bot with monitoring
docker-compose -f docker-compose.prod.yml up -d --scale review-bot=2

# View monitoring stack status
docker-compose -f docker-compose.prod.yml ps
```

## Access URLs

### Development
- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
- **Node Exporter**: http://localhost:9100/metrics
- **cAdvisor**: http://localhost:8080
- **AlertManager**: http://localhost:9093
- **Review Bot Metrics**: http://localhost:8000/metrics
- **Review Bot Health**: http://localhost:8001/health

### Production
- **Prometheus**: http://prometheus:9090 (internal)
- **Grafana**: https://grafana.review-bot.example.com
- **AlertManager**: https://alertmanager.review-bot.example.com
- **Review Bot**: https://review-bot.example.com

## Security Considerations

### Network Security
- Separate monitoring network
- Internal service communication
- Controlled port exposure

### Authentication
- Grafana password protection
- TLS termination at Traefik
- Cookie security enabled

### Data Protection
- Sensitive data redaction in logs
- Secure environment variable handling
- Read-only filesystem access where possible

## Troubleshooting

### Common Issues
1. **Services not starting**:
   - Check port conflicts
   - Verify Docker permissions
   - Check resource limits

2. **Metrics not collected**:
   - Verify service discovery
   - Check network connectivity
   - Review Prometheus configuration

3. **Alerts not firing**:
   - Check AlertManager configuration
   - Verify SMTP settings
   - Review alert rules

### Debug Commands
```bash
# Check service health
docker-compose ps
docker-compose logs prometheus

# Test metrics collection
curl http://localhost:9090/targets
curl http://localhost:8000/metrics

# Test alerts
curl http://localhost:9093/api/v1/alerts
```

## Performance Considerations

### Resource Allocation
- **Prometheus**: 2GB memory, 1 CPU core
- **Grafana**: 1GB memory, 0.5 CPU core
- **Node Exporter**: 128MB memory, 0.05 CPU core
- **cAdvisor**: 256MB memory, 0.1 CPU core

### Data Retention
- **Development**: 15 days
- **Production**: 30 days
- **Optimization**: Consider external storage for long-term retention

## Maintenance

### Regular Tasks
1. **Backup Grafana dashboards**
2. **Review alert rules**
3. **Update monitoring configuration**
4. **Monitor resource usage**

### Scaling Considerations
- Horizontal scaling with Prometheus federation
- Grafana clustering for high availability
- Load balancing for dashboard access
- Distributed storage for large deployments