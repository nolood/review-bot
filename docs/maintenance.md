# Maintenance Procedures

## Overview

This guide covers ongoing maintenance tasks, procedures, and best practices for keeping the GLM Code Review Bot running smoothly in production. Regular maintenance ensures system reliability, security, and optimal performance.

## Maintenance Schedule

### Daily Tasks

#### Health Checks
- [ ] Verify all services are running
- [ ] Check error rates in logs
- [ ] Monitor resource usage
- [ ] Review API response times
- [ ] Check backup completion

```bash
#!/bin/bash
# scripts/daily-health-check.sh

echo "=== Daily Health Check ==="

# Check service status
echo "Checking service status..."
docker ps | grep review-bot || echo "❌ Review bot container not running"

# Check health endpoints
echo "Checking health endpoints..."
curl -f https://review-bot.example.com/health || echo "❌ Health endpoint failed"

# Check error rates
echo "Checking error rates (last 24h)..."
ERROR_COUNT=$(docker logs review-bot --since=24h | grep -c ERROR || echo "0")
if [ "$ERROR_COUNT" -gt 10 ]; then
    echo "⚠️  High error count: $ERROR_COUNT"
else
    echo "✅ Error count acceptable: $ERROR_COUNT"
fi

# Check resource usage
echo "Checking resource usage..."
docker stats --no-stream review-bot

# Check disk space
echo "Checking disk space..."
df -h | grep -E "/$|/var" | awk '{print $5}' | grep -E "9[0-9]%" && echo "⚠️  High disk usage"

echo "=== Daily Health Check Complete ==="
```

#### Log Review
- [ ] Review critical error messages
- [ ] Monitor security events
- [ ] Check for unusual activity patterns
- [ ] Validate log rotation

```bash
#!/bin/bash
# scripts/daily-log-review.sh

echo "=== Daily Log Review ==="

# Check for critical errors
echo "Checking for critical errors..."
docker logs review-bot --since=24h | grep -i "critical\|fatal" || echo "✅ No critical errors"

# Check for security events
echo "Checking security events..."
docker logs review-bot --since=24h | grep -i "unauthorized\|forbidden\|security breach" || echo "✅ No security issues"

# Check API rate limiting
echo "Checking API rate limiting..."
docker logs review-bot --since=24h | grep "rate limit" | tail -5

# Check performance issues
echo "Checking performance issues..."
docker logs review-bot --since=24h | grep -i "timeout\|slow\|performance" | tail -5

echo "=== Daily Log Review Complete ==="
```

### Weekly Tasks

#### Performance Analysis
- [ ] Review response time trends
- [ ] Analyze resource utilization
- [ ] Check cache hit rates
- [ ] Review API usage patterns
- [ ] Update performance baselines

```bash
#!/bin/bash
# scripts/weekly-performance-analysis.sh

echo "=== Weekly Performance Analysis ==="

# Get average response times
echo "Average API response times:"
curl -s https://review-bot.example.com/metrics | \
  grep "http_request_duration_seconds" | \
  grep "mean" || echo "No metrics available"

# Resource utilization trends
echo "Resource utilization (7 days):"
docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" review-bot

# Cache performance
echo "Cache performance:"
redis-cli info stats | grep -E "keyspace|hits|misses" || echo "Redis metrics not available"

# Generate performance report
cat > /tmp/performance-report-$(date +%Y%m%d).txt << EOF
Performance Report - $(date)
================================
Service Status: $(systemctl is-active docker 2>/dev/null || echo "Docker running")
Container Uptime: $(docker inspect review-bot --format='{{.State.StartedAt}}')
Memory Usage: $(docker stats --no-stream review-bot --format '{{.MemUsage}}')
CPU Usage: $(docker stats --no-stream review-bot --format '{{.CPUPerc}}')
Disk Usage: $(df -h / | tail -1 | awk '{print $5}')

Recent Errors:
$(docker logs review-bot --since=7d | grep ERROR | tail -10)
EOF

echo "Performance report saved to /tmp/performance-report-$(date +%Y%m%d).txt"
echo "=== Weekly Performance Analysis Complete ==="
```

#### Security Audit
- [ ] Review access logs
- [ ] Check for unauthorized access attempts
- [ ] Validate SSL certificates
- [ ] Review API token usage
- [ ] Scan for security vulnerabilities

```bash
#!/bin/bash
# scripts/weekly-security-audit.sh

echo "=== Weekly Security Audit ==="

# Check SSL certificate expiry
echo "Checking SSL certificates..."
SSL_DOMAIN="review-bot.example.com"
SSL_EXPIRY=$(echo | openssl s_client -servername $SSL_DOMAIN -connect $SSL_DOMAIN:443 2>/dev/null | \
  openssl x509 -noout -dates | grep notAfter | cut -d= -f2)
DAYS_TO_EXPIRY=$(( ($(date -d "$SSL_EXPIRY" +%s) - $(date +%s)) / 86400 ))

if [ "$DAYS_TO_EXPIRY" -lt 30 ]; then
    echo "⚠️  SSL certificate expires in $DAYS_TO_EXPIRY days"
else
    echo "✅ SSL certificate valid for $DAYS_TO_EXPIRY days"
fi

# Check for failed authentication attempts
echo "Checking authentication failures..."
FAILED_AUTH=$(docker logs review-bot --since=7d | grep -i "unauthorized\|authentication failed" | wc -l)
if [ "$FAILED_AUTH" -gt 50 ]; then
    echo "⚠️  High number of failed authentications: $FAILED_AUTH"
else
    echo "✅ Failed authentications within normal range: $FAILED_AUTH"
fi

# Review API token usage patterns
echo "Checking API token usage..."
# This would require integration with your monitoring system
echo "Token usage analysis should be implemented based on your monitoring setup"

# Scan for common security issues
echo "Running security vulnerability scan..."
if command -v safety &> /dev/null; then
    safety check || echo "⚠️  Security vulnerabilities found"
else
    echo "Safety not installed, skipping vulnerability scan"
fi

echo "=== Weekly Security Audit Complete ==="
```

### Monthly Tasks

#### System Updates
- [ ] Update Docker images
- [ ] Apply security patches
- [ ] Update Python dependencies
- [ ] Review and update configurations
- [ ] Test disaster recovery procedures

```bash
#!/bin/bash
# scripts/monthly-system-update.sh

echo "=== Monthly System Update ==="

# Create backup before updates
./scripts/backup.sh

# Update Docker images
echo "Updating Docker images..."
docker-compose -f docker-compose.prod.yml pull

# Check for new base image updates
echo "Checking for base image updates..."
docker pull python:3.11-slim
docker pull alpine:latest

# Update Python dependencies
echo "Updating Python dependencies..."
docker-compose -f docker-compose.prod.yml run --rm review-bot pip-review --local

# Security patching
echo "Applying security patches..."
if command -v apt-get &> /dev/null; then
    sudo apt-get update && sudo apt-get upgrade -y
elif command -v yum &> /dev/null; then
    sudo yum update -y
fi

# Test disaster recovery
echo "Testing disaster recovery procedures..."
./scripts/test-recovery.sh

echo "=== Monthly System Update Complete ==="
```

#### Capacity Planning
- [ ] Review resource utilization trends
- [ ] Plan for future growth
- [ ] Update scaling thresholds
- [ ] Review storage requirements
- [ ] Update budget forecasts

```bash
#!/bin/bash
# scripts/monthly-capacity-planning.sh

echo "=== Monthly Capacity Planning ==="

# Analyze resource trends
echo "Analyzing resource utilization trends..."
docker stats --no-stream review-bot --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"

# Storage analysis
echo "Storage usage analysis..."
df -h
docker system df

# Growth projections
CURRENT_MEMORY=$(docker stats --no-stream review-bot --format '{{.MemPerc}}' | sed 's/%//')
if (( $(echo "$CURRENT_MEMORY > 0.8" | bc -l) )); then
    echo "⚠️  Memory usage above 80%, consider scaling up"
fi

# Generate capacity report
cat > /tmp/capacity-report-$(date +%Y%m%d).txt << EOF
Capacity Planning Report - $(date)
=================================
Current Memory Usage: $CURRENT_MEMORY%
Current CPU Usage: $(docker stats --no-stream review-bot --format '{{.CPUPerc}}')
Storage Usage: $(df -h / | tail -1 | awk '{print $5}')
Network I/O: $(docker stats --no-stream review-bot --format '{{.NetIO}}')

Recommendations:
$(if (( $(echo "$CURRENT_MEMORY > 0.8" | bc -l) )); then echo "- Consider increasing memory allocation"; fi)
$(if [ "$(df -h / | tail -1 | awk '{print $5}' | sed 's/%//')" -gt 80 ]; then echo "- Consider increasing storage capacity"; fi)
EOF

echo "Capacity report saved to /tmp/capacity-report-$(date +%Y%m%d).txt"
echo "=== Monthly Capacity Planning Complete ==="
```

## Emergency Procedures

### Service Outage Response

#### 1. Immediate Assessment (First 5 minutes)
```bash
#!/bin/bash
# scripts/emergency-assessment.sh

echo "=== Emergency Assessment ==="

# Check service status
echo "Service Status:"
docker ps | grep review-bot || echo "❌ Review bot not running"

# Check system resources
echo "System Resources:"
free -h
df -h
uptime

# Check network connectivity
echo "Network Connectivity:"
ping -c 3 gitlab.com || echo "❌ Cannot reach GitLab"
ping -c 3 api.z.ai || echo "❌ Cannot reach GLM API"

# Check recent errors
echo "Recent Errors (last hour):"
docker logs review-bot --since=1h | grep ERROR | tail -10

echo "=== Emergency Assessment Complete ==="
```

#### 2. Service Restoration (Next 15 minutes)
```bash
#!/bin/bash
# scripts/emergency-restoration.sh

echo "=== Emergency Service Restoration ==="

# Attempt basic restart
echo "Attempting service restart..."
docker-compose -f docker-compose.prod.yml restart review-bot

# Wait for service to be ready
sleep 30

# Verify health
echo "Verifying service health..."
for i in {1..10}; do
    if curl -f https://review-bot.example.com/health; then
        echo "✅ Service restored successfully"
        exit 0
    fi
    echo "Attempt $i/10 failed, waiting..."
    sleep 10
done

# If restart failed, try full redeployment
echo "Basic restart failed, attempting full redeployment..."
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d

# Final verification
sleep 60
if curl -f https://review-bot.example.com/health; then
    echo "✅ Service restored via redeployment"
else
    echo "❌ Automatic restoration failed, manual intervention required"
    exit 1
fi
```

### Data Recovery Procedures

#### 1. Partial Data Loss
```bash
#!/bin/bash
# scripts/partial-data-recovery.sh

echo "=== Partial Data Recovery ==="

# Identify affected time range
read -p "Enter start time for recovery (YYYY-MM-DD HH:MM:SS): " START_TIME
read -p "Enter end time for recovery (YYYY-MM-DD HH:MM:SS): " END_TIME

# Restore from backups
BACKUP_DIR="/opt/backups/review-bot"
LATEST_BACKUP=$(ls -t "$BACKUP_DIR" | head -1)

echo "Restoring from backup: $LATEST_BACKUP"

# Restore configurations
tar -xzf "$BACKUP_DIR/$LATEST_BACKUP/config-"*.tar.gz

# Restore data if needed
if [ -f "$BACKUP_DIR/$LATEST_BACKUP/data-"*.tar.gz ]; then
    docker-compose -f docker-compose.prod.yml down
    docker run --rm -v review-bot_data:/data -v "$BACKUP_DIR/$LATEST_BACKUP":/backup \
        alpine tar xzf "/backup/data-"*.tar.gz -C /data
    docker-compose -f docker-compose.prod.yml up -d
fi

echo "=== Partial Data Recovery Complete ==="
```

#### 2. Complete Data Recovery
```bash
#!/bin/bash
# scripts/complete-data-recovery.sh

echo "=== Complete Data Recovery ==="

# Select backup to restore
BACKUP_DIR="/opt/backups/review-bot"
echo "Available backups:"
ls -la "$BACKUP_DIR"

read -p "Enter backup date to restore (YYYYMMDD): " BACKUP_DATE

# Validate backup exists
if [ ! -d "$BACKUP_DIR/$BACKUP_DATE" ]; then
    echo "❌ Backup not found: $BACKUP_DATE"
    exit 1
fi

# Stop all services
echo "Stopping all services..."
docker-compose -f docker-compose.prod.yml down

# Restore everything
echo "Restoring configurations..."
tar -xzf "$BACKUP_DIR/$BACKUP_DATE/config-$BACKUP_DATE.tar.gz"

echo "Restoring data volumes..."
docker run --rm -v review-bot_data:/data -v "$BACKUP_DIR/$BACKUP_DATE":/backup \
    alpine tar xzf "/backup/data-$BACKUP_DATE.tar.gz" -C /data

echo "Restoring database..."
if [ -f "$BACKUP_DIR/$BACKUP_DATE/db-$BACKUP_DATE.sql" ]; then
    # Implement database restoration based on your DB setup
    echo "Database restoration would be implemented here"
fi

# Restart services
echo "Restarting services..."
docker-compose -f docker-compose.prod.yml up -d

# Verify restoration
sleep 60
if curl -f https://review-bot.example.com/health; then
    echo "✅ Complete data recovery successful"
else
    echo "❌ Recovery verification failed"
    exit 1
fi

echo "=== Complete Data Recovery Complete ==="
```

## Monitoring and Alerting

### Key Metrics to Monitor

#### Application Metrics
- Request response times
- Error rates by endpoint
- Token usage patterns
- Concurrent processing counts
- Queue depth (if using job queues)

#### Infrastructure Metrics
- CPU and memory utilization
- Disk space and I/O
- Network latency and throughput
- Docker container health
- Database performance (if applicable)

#### Business Metrics
- Number of reviews completed
- Average review time
- User satisfaction scores
- API cost tracking
- Security incident counts

### Alert Thresholds

```yaml
# monitoring/alert-rules.yml
groups:
- name: review-bot-alerts
  rules:
  # High error rate
  - alert: HighErrorRate
    expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.1
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "High error rate detected"
      description: "Error rate is {{ $value }} errors per second"

  # Service down
  - alert: ServiceDown
    expr: up{job="review-bot"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: "Review bot service is down"
      description: "The review bot service has been down for more than 1 minute"

  # High memory usage
  - alert: HighMemoryUsage
    expr: container_memory_usage_bytes{name="review-bot"} / container_spec_memory_limit_bytes{name="review-bot"} > 0.9
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High memory usage"
      description: "Memory usage is above 90% for 10 minutes"

  # High response time
  - alert: HighResponseTime
    expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 30
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: "High response time"
      description: "95th percentile response time is {{ $value }} seconds"
```

### Automated Responses

```bash
#!/bin/bash
# scripts/auto-response.sh

ALERT_TYPE=$1
SEVERITY=$2

case $ALERT_TYPE in
    "ServiceDown")
        if [ "$SEVERITY" = "critical" ]; then
            echo "Critical service down detected, attempting auto-recovery..."
            ./scripts/emergency-restoration.sh
            # Send notification
            curl -X POST "https://hooks.slack.com/your-webhook" \
                -H 'Content-type: application/json' \
                --data "{\"text\":\"🚨 Review Bot Service Down - Auto-recovery initiated\"}"
        fi
        ;;
    "HighErrorRate")
        echo "High error rate detected, gathering diagnostics..."
        ./scripts/gather-diagnostics.sh
        ;;
    "HighMemoryUsage")
        echo "High memory usage detected, attempting cleanup..."
        docker system prune -f
        docker-compose -f docker-compose.prod.yml restart review-bot
        ;;
esac
```

## Security Maintenance

### Regular Security Tasks

#### Certificate Management
```bash
#!/bin/bash
# scripts/certificate-management.sh

echo "=== Certificate Management ==="

# Check certificate expiry
DOMAIN="review-bot.example.com"
DAYS_TO_EXPIRY=$(echo | openssl s_client -servername $DOMAIN -connect $DOMAIN:443 2>/dev/null | \
  openssl x509 -noout -dates | grep notAfter | cut -d= -f2 | \
  awk '{print ($1-$2)/(86400)}' | sed 's/-//')

if [ "$DAYS_TO_EXPIRY" -lt 30 ]; then
    echo "⚠️  Certificate expires in $DAYS_TO_EXPIRY days"
    
    # Auto-renew certificate (using Let's Encrypt example)
    if command -v certbot &> /dev/null; then
        echo "Attempting certificate renewal..."
        certbot renew --quiet
        docker-compose -f docker-compose.prod.yml restart traefik
    else
        echo "⚠️  Manual certificate renewal required"
        # Send notification
        curl -X POST "https://hooks.slack.com/your-webhook" \
            -H 'Content-type: application/json' \
            --data "{\"text\":\"🔐 SSL Certificate Expiring Soon - Manual renewal required\"}"
    fi
else
    echo "✅ Certificate valid for $DAYS_TO_EXPIRY days"
fi
```

#### Access Control Review
```bash
#!/bin/bash
# scripts/access-control-review.sh

echo "=== Access Control Review ==="

# Review API tokens
echo "Reviewing API token usage..."
# This would integrate with your token management system

# Check for unusual access patterns
echo "Checking for unusual access patterns..."
docker logs review-bot --since=7d | grep -i "unauthorized\|forbidden" | \
    awk '{print $1, $2}' | sort | uniq -c | sort -nr | head -10

# Review user permissions (if applicable)
echo "Reviewing user permissions..."
# This would integrate with your user management system

echo "=== Access Control Review Complete ==="
```

### Security Incident Response

#### 1. Incident Triage
```bash
#!/bin/bash
# scripts/security-incident-triage.sh

echo "=== Security Incident Triage ==="

INCIDENT_TYPE=$1
SEVERITY=$2

case $INCIDENT_TYPE in
    "UnauthorizedAccess")
        echo "Unauthorized access incident detected"
        # Gather evidence
        docker logs review-bot --since=24h | grep -i "unauthorized" > /tmp/security-evidence.log
        
        # Block malicious IPs (example)
        MALICIOUS_IPS=$(docker logs review-bot --since=24h | grep "unauthorized" | \
            awk '{print $1}' | sort | uniq -c | sort -nr | head -5 | awk '{print $2}')
        
        for IP in $MALICIOUS_IPS; do
            echo "Blocking IP: $IP"
            # Implement IP blocking based on your firewall
        done
        ;;
    "DataBreach")
        echo "Potential data breach incident detected"
        # Immediate containment
        docker-compose -f docker-compose.prod.yml down
        
        # Preserve evidence
        docker logs review-bot > /tmp/breach-evidence.log
        docker export review-bot > /tmp/breach-container.tar
        
        # Notify security team
        curl -X POST "https://hooks.slack.com/your-security-webhook" \
            -H 'Content-type: application/json' \
            --data "{\"text\":\"🚨 POTENTIAL DATA BREACH - Immediate attention required\"}"
        ;;
esac

echo "=== Security Incident Triage Complete ==="
```

## Documentation Maintenance

### Regular Updates Required

#### Configuration Documentation
- Update `.env.example` with new variables
- Document new features in `docs/features/`
- Update API documentation in `docs/api/`
- Maintain `CHANGELOG.md`

#### Operational Documentation
- Update runbooks for new procedures
- Document learned incident responses
- Update contact information
- Maintain architecture diagrams

#### Security Documentation
- Update security policies
- Document new threats and mitigations
- Maintain compliance requirements
- Update incident response procedures

### Documentation Review Schedule

- **Weekly**: Review and update incident logs
- **Monthly**: Review and update operational procedures
- **Quarterly**: Comprehensive documentation audit
- **Annually**: Complete security documentation review

## Performance Tuning

### Regular Optimization Tasks

#### Database Optimization (if applicable)
```sql
-- Database maintenance queries
ANALYZE;
VACUUM;
REINDEX;

-- Check query performance
SELECT query, mean_time, calls 
FROM pg_stat_statements 
ORDER BY mean_time DESC 
LIMIT 10;
```

#### Cache Optimization
```bash
#!/bin/bash
# scripts/cache-optimization.sh

echo "=== Cache Optimization ==="

# Redis memory analysis
redis-cli info memory | grep -E "used_memory|maxmemory"

# Clear expired cache entries
redis-cli --scan --pattern "expired:*" | xargs redis-cli del

# Optimize Redis configuration
redis-cli config set maxmemory-policy allkeys-lru

# Monitor cache hit rates
redis-cli info stats | grep -E "keyspace_hits|keyspace_misses"
```

#### Application Performance
```bash
#!/bin/bash
# scripts/performance-tuning.sh

echo "=== Performance Tuning ==="

# Profile application performance
docker-compose -f docker-compose.prod.yml exec review-bot \
    python -m cProfile -o /tmp/profile.stats review_bot.py

# Analyze profiling results
python -c "
import pstats
p = pstats.Stats('/tmp/profile.stats')
p.sort_stats('cumulative').print_stats(20)
"

# Update configuration based on performance data
# This would analyze the results and suggest configuration changes

echo "=== Performance Tuning Complete ==="
```

This comprehensive maintenance guide provides all necessary procedures for keeping the GLM Code Review Bot running reliably and securely in production. Regular execution of these procedures ensures optimal performance, security, and availability of the service.