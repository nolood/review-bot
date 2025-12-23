#!/bin/bash

# Deployment script for review-bot
# Usage: ./scripts/deploy.sh [environment] [version]
# Environments: staging, production
# Version: image tag (default: latest)

set -e

ENVIRONMENT=${1:-"staging"}
VERSION=${2:-"latest"}
DEPLOY_PATH="/opt/review-bot"
BACKUP_PATH="/opt/review-bot-backup"

echo "Deploying review-bot to $ENVIRONMENT environment with version $VERSION"

# Load environment-specific variables
if [ "$ENVIRONMENT" = "production" ]; then
    COMPOSE_FILE="docker-compose.yml:docker-compose.prod.yml"
    SERVICE_NAME="review-bot"
else
    COMPOSE_FILE="docker-compose.yml:docker-compose.staging.yml"
    SERVICE_NAME="review-bot"
fi

# Create backup of current deployment
if [ -d "$DEPLOY_PATH" ]; then
    echo "Creating backup of current deployment..."
    rm -rf "$BACKUP_PATH"
    cp -r "$DEPLOY_PATH" "$BACKUP_PATH"
fi

# Ensure deploy directory exists
mkdir -p "$DEPLOY_PATH"
cd "$DEPLOY_PATH"

# Download latest docker-compose files
echo "Downloading deployment configuration..."
# This would typically download from your config repository
# For now, assume files are already in place

# Pull new images
echo "Pulling new Docker images..."
IMAGE_REGISTRY="registry.gitlab.com/your-group/review-bot"
docker pull "$IMAGE_REGISTRY:$VERSION"

# Update image tag in docker-compose
sed -i "s|image:.*registry.gitlab.com.*|image: $IMAGE_REGISTRY:$VERSION|g" docker-compose.yml

# Deploy with blue-green strategy
if [ "$ENVIRONMENT" = "production" ]; then
    echo "Performing blue-green deployment for production..."
    
    # Start new version
    docker-compose -f $COMPOSE_FILE up -d --no-deps --scale review-bot-new=1 review-bot-new
    
    # Health check new version
    echo "Checking health of new deployment..."
    if ! ./scripts/health-check.sh review-bot-new; then
        echo "❌ New deployment failed health check, rolling back..."
        docker-compose -f $COMPOSE_FILE stop review-bot-new
        docker-compose -f $COMPOSE_FILE rm -f review-bot-new
        exit 1
    fi
    
    # Switch traffic to new version
    echo "Switching traffic to new version..."
    docker-compose -f $COMPOSE_FILE stop review-bot-old || true
    docker-compose -f $COMPOSE_FILE up -d review-bot
    
    # Stop old version after successful switch
    echo "Cleaning up old deployment..."
    docker-compose -f $COMPOSE_FILE stop review-bot-new
    docker-compose -f $COMPOSE_FILE rm -f review-bot-new
    
else
    echo "Deploying to staging..."
    docker-compose -f $COMPOSE_FILE up -d
    
    # Health check
    if ! ./scripts/health-check.sh; then
        echo "❌ Staging deployment failed health check"
        exit 1
    fi
fi

echo "✅ Deployment to $ENVIRONMENT completed successfully"

# Cleanup old images
echo "Cleaning up old Docker images..."
docker image prune -f

# Keep backup for rollback (optional)
# rm -rf "$BACKUP_PATH"