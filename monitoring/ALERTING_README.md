# Monitoring Alerting Configuration

This document describes the comprehensive alerting rules and notification configuration for the Review Bot monitoring system.

## Overview

The monitoring system uses Prometheus for metrics collection and AlertManager for alert routing and notifications. The system provides comprehensive monitoring of:

- Review Bot application health and performance
- API response times (GLM and GitLab)
- Resource usage (CPU, memory, disk)
- Token usage and rate limits
- System infrastructure health
- Monitoring stack health

## Alerting Rules

### Review Bot Application Alerts

#### Critical Alerts

| Alert Name | Trigger | Threshold | Duration | Severity |
|------------|---------|-----------|----------|----------|
| `ReviewBotDown` | `up{job="review-bot"} == 0` | Service unavailable | 2m | critical |
| `ReviewBotCriticalErrorRate` | Error rate > 20% | `rate(errors/requests) > 0.2` | 1m | critical |
| `ReviewBotCriticalSlowGLMAPI` | GLM API response time > 5s | `histogram_quantile(0.95) > 5` | 2m | critical |
| `ReviewBotCriticalSlowGitLabAPI` | GitLab API response time > 3s | `histogram_quantile(0.95) > 3` | 2m | critical |
| `ReviewBotCriticalMemoryUsage` | Memory usage > 95% | `container_memory_usage/container_spec_memory > 0.95` | 2m | critical |
| `ReviewBotCriticalCPUUsage` | CPU usage > 95% | `rate(container_cpu_usage) > 0.95` | 2m | critical |
| `ReviewBotCriticalTokenUsage` | Token usage > 95% of daily limit | `tokens_used/token_limit > 0.95` | 0m | critical |
| `ReviewBotGitLabRateLimitExceeded` | GitLab API rate limit exceeded | `increase(rate_limit_exceeded) > 0` | 0m | critical |

#### Warning Alerts

| Alert Name | Trigger | Threshold | Duration | Severity |
|------------|---------|-----------|----------|----------|
| `ReviewBotHighErrorRate` | Error rate > 5% | `rate(errors/requests) > 0.05` | 3m | warning |
| `ReviewBotSlowGLMAPI` | GLM API response time > 2s | `histogram_quantile(0.95) > 2` | 5m | warning |
| `ReviewBotSlowGitLabAPI` | GitLab API response time > 1s | `histogram_quantile(0.95) > 1` | 5m | warning |
| `ReviewBotHighMemoryUsage` | Memory usage > 85% | `container_memory_usage/container_spec_memory > 0.85` | 5m | warning |
| `ReviewBotHighCPUUsage` | CPU usage > 80% | `rate(container_cpu_usage) > 0.8` | 5m | warning |
| `ReviewBotHighTokenUsage` | Token usage > 80% of daily limit | `tokens_used/token_limit > 0.8` | 0m | warning |
| `ReviewBotGitLabRateLimitWarning` | GitLab rate limit remaining < 100 | `rate_limit_remaining < 100` | 0m | warning |

### System Infrastructure Alerts

#### Critical Alerts

| Alert Name | Trigger | Threshold | Duration | Severity |
|------------|---------|-----------|----------|----------|
| `CriticalDiskUsage` | Disk usage > 95% | `(total-free)/total > 0.95` | 1m | critical |
| `CriticalMemoryUsage` | Memory usage > 95% | `(total-available)/total > 0.95` | 2m | critical |
| `CriticalCPUUsage` | CPU usage > 95% | `100 - idle_percent > 95` | 2m | critical |
| `ContainerDown` | Container unavailable | `up == 0` | 2m | critical |
| `ContainerOOMKilled` | Container OOM event | `increase(oom_events) > 0` | 0m | critical |

#### Warning Alerts

| Alert Name | Trigger | Threshold | Duration | Severity |
|------------|---------|-----------|----------|----------|
| `HighDiskUsage` | Disk usage > 85% | `(total-free)/total > 0.85` | 5m | warning |
| `HighMemoryUsage` | Memory usage > 85% | `(total-available)/total > 0.85` | 5m | warning |
| `HighCPUUsage` | CPU usage > 80% | `100 - idle_percent > 80` | 5m | warning |
| `ContainerRestarting` | Container restarts > 3/hour | `increase(start_time_seconds) > 3` | 0m | warning |

### Monitoring Stack Alerts

| Alert Name | Trigger | Threshold | Duration | Severity |
|------------|---------|-----------|----------|----------|
| `PrometheusDown` | Prometheus unavailable | `up{job="prometheus"} == 0` | 2m | critical |
| `PrometheusConfigReloadFailed` | Configuration reload failed | `config_last_reload_successful == 0` | 0m | critical |
| `GrafanaDown` | Grafana unavailable | `up{job="grafana"} == 0` | 2m | warning |
| `AlertManagerDown` | AlertManager unavailable | `up{job="alertmanager"} == 0` | 2m | warning |
| `AlertManagerConfigReloadFailed` | Configuration reload failed | `config_last_reload_successful == 0` | 0m | warning |

### Network Alerts

| Alert Name | Trigger | Threshold | Duration | Severity |
|------------|---------|-----------|----------|----------|
| `NetworkConnectivityIssue` | Probe failed | `probe_success == 0` | 1m | critical |
| `HighNetworkLatency` | High latency | `probe_duration_seconds > 0.5` | 5m | warning |

## Notification Configuration

### Email Receivers

| Receiver | Email Address | Use Case |
|----------|---------------|----------|
| `default-receiver` | `${DEFAULT_EMAIL}` | Default unmatched alerts |
| `critical-alerts` | `${CRITICAL_EMAIL}` | All critical alerts |
| `warning-alerts` | `${WARNING_EMAIL}` | Warning alerts |
| `info-alerts` | `${INFO_EMAIL}` | Informational alerts |
| `review-bot-alerts` | `${REVIEW_BOT_EMAIL}` | Review Bot general alerts |
| `review-bot-critical-alerts` | `${REVIEW_BOT_CRITICAL_EMAIL}` | Review Bot critical alerts |
| `review-bot-api-alerts` | `${REVIEW_BOT_API_EMAIL}` | Review Bot API alerts |
| `review-bot-resource-alerts` | `${REVIEW_BOT_RESOURCE_EMAIL}` | Review Bot resource alerts |
| `review-bot-token-alerts` | `${REVIEW_BOT_TOKEN_EMAIL}` | Review Bot token alerts |
| `monitoring-critical-alerts` | `${MONITORING_CRITICAL_EMAIL}` | Monitoring stack critical alerts |
| `system-critical-alerts` | `${SYSTEM_CRITICAL_EMAIL}` | System critical alerts |
| `system-warning-alerts` | `${SYSTEM_WARNING_EMAIL}` | System warning alerts |

### Slack Integration

Slack notifications are configured for:

- `#alerts-critical` - Critical alerts from all services
- `#alerts-warning` - Warning alerts from all services
- `#review-bot-alerts` - Review Bot general alerts
- `#review-bot-critical` - Review Bot critical alerts

### Webhook Integration

Webhook endpoints are configured for:

- Teams integration (`${WEBHOOK_URL}`)
- PagerDuty integration for critical monitoring alerts
- System critical alerts via `${SYSTEM_WEBHOOK_URL}`

## Alert Routing and Grouping

### Grouping Strategy

Alerts are grouped by:
- `alertname` - Groups same alerts together
- `cluster` - Groups by infrastructure cluster
- `service` - Groups by application service
- `severity` - Groups by alert severity
- `component` - Groups by application component

### Routing Logic

1. **Critical Alerts** - Immediate routing with 5s group wait, 10m repeat interval
2. **Warning Alerts** - Standard routing with 30s group wait, 30m repeat interval
3. **Info Alerts** - Low priority with 60s group wait, 24h repeat interval
4. **Service-Specific** - Additional routing based on service and component

### Inhibition Rules

To prevent alert spam, the following inhibition rules are configured:

1. **Critical inhibits Warning** - Critical alerts suppress warning alerts for the same service
2. **ReviewBotDown inhibits all Review Bot alerts**
3. **System critical resource alerts inhibit application resource alerts**
4. **GitLab rate limit exceeded inhibits slow GitLab API alerts**
5. **Container down inhibits container restart alerts**
6. **Monitoring critical alerts inhibit monitoring warning alerts**

## Environment Variables

### SMTP Configuration

```bash
SMTP_HOST=smtp.example.com:587
SMTP_FROM=alertmanager@example.com
SMTP_USER=alertmanager@example.com
SMTP_PASSWORD=your-smtp-password
```

### Email Recipients

```bash
DEFAULT_EMAIL=admin@example.com
CRITICAL_EMAIL=admin@example.com,support@example.com
WARNING_EMAIL=dev-team@example.com
INFO_EMAIL=dev-team@example.com
REVIEW_BOT_EMAIL=review-bot-team@example.com
REVIEW_BOT_CRITICAL_EMAIL=review-bot-team@example.com,admin@example.com
REVIEW_BOT_API_EMAIL=api-team@example.com
REVIEW_BOT_RESOURCE_EMAIL=infra-team@example.com
REVIEW_BOT_TOKEN_EMAIL=review-bot-team@example.com,billing@example.com
MONITORING_CRITICAL_EMAIL=infra-team@example.com,admin@example.com
SYSTEM_CRITICAL_EMAIL=infra-team@example.com,admin@example.com
SYSTEM_WARNING_EMAIL=infra-team@example.com
```

### Webhook Configuration

```bash
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK
WEBHOOK_URL=http://teams-webhook:80
WEBHOOK_USER=teams-user
WEBHOOK_PASSWORD=teams-password
MONITORING_WEBHOOK_URL=http://pagerduty-webhook:80
SYSTEM_WEBHOOK_URL=http://pagerduty-webhook:80
```

### PagerDuty Configuration

```bash
PAGERDUTY_SERVICE_KEY=your-pagerduty-service-key
MONITORING_PAGERDUTY_SERVICE_KEY=monitoring-pagerduty-key
SYSTEM_PAGERDUTY_SERVICE_KEY=system-pagerduty-key
```

## Email Templates

The system includes comprehensive email templates:

- **Default Template** - General purpose alert notification
- **Critical Template** - Emergency formatting for critical alerts
- **Warning Template** - Warning-specific formatting
- **Info Template** - Informational alert formatting
- **Review Bot Template** - Custom branding for Review Bot alerts

All templates include:
- Proper severity-based styling
- Runbook links and troubleshooting information
- Alert metadata (service, component, instance)
- Duration information for resolved alerts
- Mobile-responsive design

## Maintenance

### Testing Alert Rules

Test alert rules using:

```bash
# Check rule syntax
promtool check rules /etc/prometheus/rules/alerting.yml

# Test alert evaluation
promtool query instant http://localhost:9090/api/v1/query 'up{job="review-bot"}'
```

### Reloading Configuration

```bash
# Reload Prometheus rules
curl -X POST http://localhost:9090/-/reload

# Reload AlertManager configuration
curl -X POST http://localhost:9093/-/reload
```

### Monitoring AlertManager Health

Check AlertManager status:
- Web UI: http://localhost:9093
- API: http://localhost:9093/api/v1/status

## Troubleshooting

### Common Issues

1. **Emails not sending** - Check SMTP configuration and authentication
2. **Slack notifications failing** - Verify webhook URL and permissions
3. **Alerts not firing** - Check metric availability and rule syntax
4. **Too many alerts** - Review inhibition rules and threshold settings

### Debug Commands

```bash
# Check Prometheus targets
curl http://localhost:9090/api/v1/targets

# Check AlertManager configuration
curl http://localhost:9093/api/v1/status

# View active alerts
curl http://localhost:9093/api/v1/alerts
```

## Runbooks

Each alert includes a runbook URL pointing to troubleshooting guides. Key runbooks:

- [Review Bot Down](https://docs.example.com/runbooks/review-bot-down)
- [High Error Rate](https://docs.example.com/runbooks/high-error-rate)
- [Slow API Responses](https://docs.example.com/runbooks/slow-api)
- [Resource Issues](https://docs.example.com/runbooks/resource-issues)
- [Token Limits](https://docs.example.com/runbooks/token-limits)

## Best Practices

1. **Regularly review thresholds** - Adjust based on normal operating patterns
2. **Update runbooks** - Keep troubleshooting guides current
3. **Monitor alert fatigue** - Adjust thresholds if too many false positives
4. **Test notifications** - Regularly verify email and webhook delivery
5. **Document customizations** - Record any rule modifications

## Security Considerations

- SMTP credentials should be stored securely
- Webhook URLs should use HTTPS
- Rate limiting configured for external integrations
- Sensitive information redacted from alert content
- Regular rotation of API keys and tokens