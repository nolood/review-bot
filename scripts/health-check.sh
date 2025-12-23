#!/bin/bash

# Health check script for review-bot deployment
# Usage: ./scripts/health-check.sh [container_name]
# Default container name: review-bot

set -e

CONTAINER_NAME=${1:-"review-bot"}
MAX_RETRIES=30
RETRY_INTERVAL=10
HEALTH_URL="http://localhost:8000/health"

echo "Performing health check for container: $CONTAINER_NAME"

# Check if container is running
if ! docker ps | grep -q $CONTAINER_NAME; then
    echo "ERROR: Container $CONTAINER_NAME is not running"
    exit 1
fi

# Wait for container to be ready
echo "Waiting for container to be ready..."
for i in $(seq 1 $MAX_RETRIES); do
    if docker exec $CONTAINER_NAME python -c "
import sys
try:
    import requests
    response = requests.get('http://localhost:8000/health', timeout=5)
    if response.status_code == 200:
        sys.exit(0)
    else:
        sys.exit(1)
except Exception as e:
    sys.exit(1)
" 2>/dev/null; then
        echo "✅ Container health check passed"
        exit 0
    fi
    
    echo "Attempt $i/$MAX_RETRIES: Container not ready, waiting ${RETRY_INTERVAL}s..."
    sleep $RETRY_INTERVAL
done

echo "❌ Health check failed after $MAX_RETRIES attempts"
exit 1