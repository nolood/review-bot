#!/bin/bash

# Test script for Docker Compose monitoring stack

set -e

echo "🐳 Testing Docker Compose Monitoring Stack"
echo "=========================================="

# Check if Docker and Docker Compose are available
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed or not in PATH"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed or not in PATH"
    exit 1
fi

echo "✅ Docker and Docker Compose are available"

# Validate compose files
echo ""
echo "📋 Validating Docker Compose files..."

if docker-compose -f docker-compose.yml config > /dev/null 2>&1; then
    echo "✅ docker-compose.yml is valid"
else
    echo "❌ docker-compose.yml has errors"
    docker-compose -f docker-compose.yml config
    exit 1
fi

if docker-compose -f docker-compose.prod.yml config > /dev/null 2>&1; then
    echo "✅ docker-compose.prod.yml is valid"
else
    echo "❌ docker-compose.prod.yml has errors"
    docker-compose -f docker-compose.prod.yml config
    exit 1
fi

# Check monitoring configuration files
echo ""
echo "📁 Checking monitoring configuration files..."

MONITORING_DIR="./monitoring"
CONFIG_FILES=(
    "$MONITORING_DIR/prometheus.yml"
    "$MONITORING_DIR/rules/alerting.yml"
    "$MONITORING_DIR/alertmanager.yml"
    "$MONITORING_DIR/docker-exporter.yml"
)

for file in "${CONFIG_FILES[@]}"; do
    if [[ -f "$file" ]]; then
        echo "✅ $file exists"
    else
        echo "❌ $file is missing"
    fi
done

# Check Grafana configuration
echo ""
echo "📊 Checking Grafana configuration..."

if [[ -d "$MONITORING_DIR/grafana" ]]; then
    echo "✅ Grafana directory exists"
    
    if [[ -f "$MONITORING_DIR/grafana/dashboards/dashboard.yml" ]]; then
        echo "✅ Grafana dashboard configuration exists"
    else
        echo "❌ Grafana dashboard configuration is missing"
    fi
    
    if [[ -f "$MONITORING_DIR/grafana/datasources/prometheus.yml" ]]; then
        echo "✅ Grafana datasource configuration exists"
    else
        echo "❌ Grafana datasource configuration is missing"
    fi
else
    echo "❌ Grafana directory is missing"
fi

# Check AlertManager templates
echo ""
echo "📧 Checking AlertManager templates..."

if [[ -d "$MONITORING_DIR/alertmanager_templates" ]]; then
    echo "✅ AlertManager templates directory exists"
    
    if [[ -f "$MONITORING_DIR/alertmanager_templates/email.tmpl" ]]; then
        echo "✅ Email template exists"
    else
        echo "❌ Email template is missing"
    fi
else
    echo "❌ AlertManager templates directory is missing"
fi

# Check Dockerfile
echo ""
echo "🏗️  Checking Dockerfile..."

if [[ -f "Dockerfile" ]]; then
    echo "✅ Dockerfile exists"
    
    # Check for monitoring dependencies
    if grep -q "prometheus-client" Dockerfile; then
        echo "✅ Prometheus client is included in Dockerfile"
    else
        echo "❌ Prometheus client is missing from Dockerfile"
    fi
    
    if grep -q "EXPOSE 8000 8001" Dockerfile; then
        echo "✅ Monitoring ports are exposed in Dockerfile"
    else
        echo "❌ Monitoring ports are not exposed in Dockerfile"
    fi
else
    echo "❌ Dockerfile is missing"
fi

# Check requirements.txt
echo ""
echo "📦 Checking requirements.txt..."

if [[ -f "requirements.txt" ]]; then
    echo "✅ requirements.txt exists"
    
    # Check for monitoring dependencies
    if grep -q "prometheus-client" requirements.txt; then
        echo "✅ Prometheus client is in requirements.txt"
    else
        echo "❌ Prometheus client is missing from requirements.txt"
    fi
    
    if grep -q "fastapi" requirements.txt; then
        echo "✅ FastAPI is in requirements.txt"
    else
        echo "❌ FastAPI is missing from requirements.txt"
    fi
else
    echo "❌ requirements.txt is missing"
fi

# Test network connectivity simulation
echo ""
echo "🌐 Testing service port availability..."

# Check if required ports are available (basic simulation)
PORTS=(
    8000  # Review Bot Metrics
    8001  # Review Bot Health
    9090  # Prometheus
    3000  # Grafana
    9100  # Node Exporter
    8080  # cAdvisor
    9093  # AlertManager
)

for port in "${PORTS[@]}"; do
    if ! netstat -tuln 2>/dev/null | grep -q ":$port "; then
        echo "✅ Port $port is available"
    else
        echo "⚠️  Port $port is already in use"
    fi
done

# Environment variables check
echo ""
echo "🔧 Checking environment variables example..."

if [[ -f ".env.example" ]]; then
    echo "✅ .env.example exists"
    
    REQUIRED_VARS=(
        "GLM_API_KEY"
        "GITLAB_TOKEN"
        "GITLAB_API_URL"
        "GRAFANA_PASSWORD"
    )
    
    for var in "${REQUIRED_VARS[@]}"; do
        if grep -q "$var" .env.example; then
            echo "✅ $var is documented in .env.example"
        else
            echo "❌ $var is missing from .env.example"
        fi
    done
else
    echo "❌ .env.example is missing"
fi

# Performance recommendations
echo ""
echo "💡 Performance Recommendations:"
echo "--------------------------------"
echo "• Consider increasing Prometheus data retention for production"
echo "• Monitor disk usage for Prometheus time-series data"
echo "• Set up log rotation for application logs"
echo "• Consider external storage for long-term metrics"
echo "• Implement backup strategy for Grafana dashboards"
echo "• Set up monitoring for the monitoring stack itself"

# Security recommendations
echo ""
echo "🔒 Security Recommendations:"
echo "----------------------------"
echo "• Use strong passwords for Grafana admin"
echo "• Enable TLS/SSL for all web interfaces"
echo "• Restrict network access to monitoring endpoints"
echo "• Use secrets management for sensitive environment variables"
echo "• Regularly update container images"
echo "• Implement proper authentication for monitoring endpoints"

echo ""
echo "🎉 Docker Compose monitoring stack validation completed!"
echo ""
echo "📋 Next Steps:"
echo "1. Copy .env.example to .env and configure variables"
echo "2. Run: docker-compose up -d to start development stack"
echo "3. Run: docker-compose -f docker-compose.prod.yml up -d for production"
echo "4. Access Grafana: http://localhost:3000"
echo "5. Access Prometheus: http://localhost:9090"
echo "6. Configure alerts and notifications as needed"