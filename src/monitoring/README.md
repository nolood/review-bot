# Monitoring Module for GLM Code Review Bot

A comprehensive monitoring and observability system for the GLM Code Review Bot, providing health checks, metrics collection, alerting, and a FastAPI-based monitoring server.

## 🏗️ Architecture

The monitoring system follows clean architecture principles with:

- **Dependency Injection**: Components are loosely coupled and easily testable
- **Async/Await Patterns**: All I/O operations use async/await for optimal performance
- **Type Safety**: Full type hints using Python 3.10+ syntax
- **Error Handling**: Comprehensive error handling with custom exceptions
- **Thread Safety**: Safe concurrent operations across all components

## 📁 Module Structure

```
src/monitoring/
├── __init__.py           # Module initialization and exports
├── health_checker.py      # Health check implementations
├── metrics_collector.py   # Prometheus metrics collection
├── monitoring_server.py   # FastAPI monitoring server
└── alerts.py            # Alerting and notification system
```

## 🏥 Health Checks

### Features
- **API Health Checks**: Monitor GitLab and GLM API endpoints
- **System Resources**: Track CPU, memory, and disk usage
- **Application Health**: Verify configuration and dependencies
- **Concurrent Execution**: Run all checks in parallel
- **Configurable Timeouts**: Per-check timeout management
- **Detailed Reporting**: Comprehensive status with metrics

### Usage
```python
from src.monitoring import HealthChecker

# Create health checker
health_checker = HealthChecker()

# Run all health checks
results = await health_checker.check_all()

# Check specific service
result = await health_checker.check_single("gitlab_api")

# Add custom health check
from src.monitoring.health_checker import APIHealthChecker
custom_check = APIHealthChecker(
    name="my_api",
    url="https://api.example.com/health",
    headers={"Authorization": "Bearer token"}
)
health_checker.add_checker(custom_check)
```

### Health Check Results
```python
{
    "overall_status": "healthy",
    "is_healthy": true,
    "total_checks": 4,
    "passed_checks": 4,
    "failed_checks": [],
    "duration_ms": 1250.5,
    "timestamp": "2024-01-01T12:00:00.000Z",
    "results": [
        {
            "name": "gitlab_api",
            "status": "healthy",
            "message": "API responding normally (status 200)",
            "duration_ms": 250.5,
            "metrics": {"status_code": 200, "response_time_ms": 200.0}
        }
    ]
}
```

## 📊 Metrics Collection

### Features
- **API Tracking**: Response times, success rates, error tracking
- **Token Usage**: GLM API token consumption monitoring
- **System Metrics**: Background resource collection
- **Prometheus Export**: Standard metrics format
- **Historical Data**: Maintain configurable history
- **Thread Safety**: Concurrent metric updates

### Usage
```python
from src.monitoring import MetricsCollector

# Create metrics collector
metrics = MetricsCollector()

# Record API request
metrics.record_api_request(
    api_name="gitlab",
    method="POST",
    status_code=200,
    response_time_ms=250.5
)

# Record token usage
metrics.record_token_usage(
    prompt_tokens=150,
    completion_tokens=75,
    model="glm-4"
)

# Get all metrics
all_metrics = metrics.get_all_metrics()

# Export Prometheus metrics
prometheus_data = metrics.get_prometheus_metrics()
```

### Available Metrics
- **API Metrics**: Request counts, response times, success rates
- **Token Metrics**: Usage by model, daily consumption, costs
- **System Metrics**: CPU, memory, disk utilization
- **Application Metrics**: Uptime, error counts

## 🖥️ Monitoring Server

### Features
- **FastAPI Server**: Modern async HTTP server
- **Health Endpoints**: Multiple health check formats
- **Metrics Endpoints**: JSON and Prometheus formats
- **Admin Interface**: Configuration and management
- **Auto Documentation**: Swagger UI and ReDoc
- **CORS Support**: Configurable cross-origin requests

### Endpoints

#### Health Checks
- `GET /health` - Basic health status
- `GET /health/detailed` - Comprehensive health report
- `GET /health/checker/{name}` - Specific health check
- `GET /health/status` - Available checkers info

#### Metrics
- `GET /metrics` - Application metrics (JSON)
- `GET /metrics/prometheus` - Prometheus format
- `GET /metrics/registries` - Available registries

#### Administration
- `GET /admin/config` - Server configuration
- `POST /admin/reset-metrics` - Reset metrics

### Usage
```python
from src.monitoring import create_monitoring_server

# Create server with default configuration
server = create_monitoring_server()

# Run synchronously
server.run()

# Or run asynchronously
await server.start_server()
```

## 🚨 Alerting System

### Features
- **Configurable Rules**: Flexible alert conditions
- **Multiple Channels**: Log, webhook, email, Slack, Discord
- **Rate Limiting**: Prevent alert spam
- **Lifecycle Management**: Acknowledge, resolve, suppress
- **Auto Resolution**: Time-based alert cleanup
- **Historical Tracking**: Alert history and statistics

### Usage
```python
from src.monitoring import AlertManager, AlertRule, AlertSeverity

# Create alert manager
alert_manager = AlertManager()

# Add custom alert rule
rule = AlertRule(
    name="high_error_rate",
    description="High API error rate detected",
    severity=AlertSeverity.WARNING,
    metric_name="error_rate",
    threshold_value=0.05,
    comparison="gt",
    consecutive_breaches=3,
    notification_channels=[NotificationChannel.WEBHOOK],
    webhook_url="https://hooks.slack.com/..."
)
alert_manager.add_rule(rule)

# Evaluate rules with current metrics
alerts = alert_manager.evaluate_rules(metrics=current_metrics)

# Acknowledge alert
alert_manager.acknowledge_alert(alert_id="alert_123", acknowledged_by="admin")
```

### Default Alert Rules
- **High CPU Usage**: >80% for 2 consecutive checks
- **High Memory Usage**: >85% for 2 consecutive checks  
- **High Disk Usage**: >90% for 1 check
- **High API Error Rate**: >10% error rate for 3 checks
- **Health Check Failure**: Critical service failures

## 🔧 Configuration

### Environment Variables
```bash
# Server Configuration
MONITORING_HOST=0.0.0.0
MONITORING_PORT=8080
MONITORING_LOG_LEVEL=info

# Health Check Timeouts
HEALTH_CHECK_TIMEOUT=30

# Metrics Collection
METRICS_COLLECTION_INTERVAL=60

# Alerting
ALERT_WEBHOOK_URL=https://hooks.slack.com/...
ALERT_COOLDOWN_MINUTES=5
ALERT_MAX_NOTIFICATIONS_PER_HOUR=10
```

### Custom Configuration
```python
from src.monitoring.monitoring_server import ServerConfig
from src.monitoring import create_monitoring_server

config = ServerConfig(
    host="127.0.0.1",
    port=9090,
    log_level="debug",
    enable_cors=True,
    cors_origins=["https://myapp.com"]
)

server = create_monitoring_server(config=config)
```

## 📈 Integration Examples

### Basic Integration
```python
from src.monitoring import (
    HealthChecker,
    MetricsCollector, 
    create_monitoring_server,
    AlertManager
)

# Create components
health_checker = HealthChecker()
metrics_collector = MetricsCollector()
alert_manager = AlertManager()

# Create monitoring server
server = create_monitoring_server(
    health_checker=health_checker,
    metrics_collector=metrics_collector
)

# Start monitoring
await server.start_server()
```

### Custom Health Check
```python
from src.monitoring.health_checker import BaseHealthChecker, HealthCheckResult, HealthStatus

class CustomHealthChecker(BaseHealthChecker):
    async def _perform_check(self) -> HealthCheckResult:
        # Custom health check logic
        return HealthCheckResult(
            name="custom_service",
            status=HealthStatus.HEALTHY,
            message="Service is healthy",
            metrics={"custom_metric": 42}
        )

health_checker.add_checker(CustomHealthChecker("custom_service"))
```

### Custom Alert Rule
```python
from src.monitoring.alerts import AlertRule, AlertSeverity, NotificationChannel

rule = AlertRule(
    name="custom_business_metric",
    description="Business metric threshold exceeded",
    severity=AlertSeverity.ERROR,
    metric_name="business_error_rate",
    threshold_value=0.02,
    comparison="gt",
    consecutive_breaches=5,
    notification_channels=[NotificationChannel.WEBHOOK, NotificationChannel.EMAIL],
    webhook_url="https://api.company.com/alerts",
    auto_resolve_minutes=30
)
alert_manager.add_rule(rule)
```

## 🔍 Monitoring Workflows

### 1. Health Monitoring
```
Health Checker → API Tests → System Tests → Aggregation → HTTP Endpoints
```

### 2. Metrics Collection  
```
API Requests → Tracking → Historical Storage → Prometheus Export → HTTP Endpoints
```

### 3. Alerting
```
Metrics Evaluation → Rule Engine → Rate Limiting → Notifications → Management
```

## 🛠️ Development

### Installation
```bash
pip install psutil prometheus-client fastapi uvicorn httpx
```

### Testing
```bash
# Run monitoring demo
python3 monitoring_demo.py

# Test individual components
python3 test_monitoring_integration.py
```

### Development Server
```python
from src.monitoring import create_monitoring_server

server = create_monitoring_server()
server.run()  # Starts on http://localhost:8080
```

## 📋 API Reference

### Health Checker API
- `HealthChecker()` - Create health checker
- `await check_all()` - Run all health checks
- `await check_single(name)` - Run specific check
- `add_checker(checker)` - Add custom checker
- `get_checker_names()` - List available checkers

### Metrics Collector API
- `MetricsCollector()` - Create metrics collector
- `record_api_request()` - Record API request
- `record_token_usage()` - Record token usage
- `get_all_metrics()` - Get all metrics
- `get_prometheus_metrics()` - Export Prometheus format

### Alert Manager API
- `AlertManager()` - Create alert manager
- `add_rule(rule)` - Add alert rule
- `evaluate_rules()` - Evaluate against metrics
- `acknowledge_alert()` - Acknowledge alert
- `resolve_alert()` - Resolve alert

### Server API
- `create_monitoring_server()` - Create server
- `server.run()` - Run synchronously
- `await server.start_server()` - Run asynchronously
- `server.get_app()` - Get FastAPI app

## 🚀 Production Deployment

### Docker Integration
```dockerfile
FROM python:3.11-slim

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/

EXPOSE 8080
CMD ["python3", "-m", "src.monitoring.monitoring_server"]
```

### Kubernetes Integration
```yaml
apiVersion: v1
kind: Service
metadata:
  name: review-bot-monitoring
spec:
  selector:
    app: review-bot-monitoring
  ports:
  - port: 8080
    targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: review-bot-monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: review-bot-monitoring
  template:
    metadata:
      labels:
        app: review-bot-monitoring
    spec:
      containers:
      - name: monitoring
        image: review-bot:latest
        ports:
        - containerPort: 8080
        env:
        - name: MONITORING_PORT
          value: "8080"
```

## 🔒 Security Considerations

- **Sensitive Data Redaction**: Automatic redaction in logs and metrics
- **CORS Configuration**: Configurable cross-origin policies
- **Authentication Ready**: Framework for API authentication
- **Secure Defaults**: Safe default configurations
- **Input Validation**: Comprehensive input sanitization

## 📊 Monitoring Best Practices

1. **Health Checks**: Configure appropriate timeouts and retry logic
2. **Metrics Collection**: Set reasonable collection intervals
3. **Alerting**: Configure meaningful thresholds and rate limits
4. **Retention**: Implement appropriate data retention policies
5. **Documentation**: Maintain clear alert descriptions and runbooks

## 🤝 Contributing

The monitoring system follows the project's architectural patterns:

- Use async/await for I/O operations
- Include comprehensive type hints
- Add detailed docstrings and comments
- Follow error handling patterns
- Write tests for new functionality
- Update documentation

## 📄 License

This monitoring module is part of the GLM Code Review Bot project and follows the same licensing terms.