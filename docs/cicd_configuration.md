# GitLab CI/CD Configuration Documentation

## Overview
This document describes the comprehensive GitLab CI/CD pipeline configuration for the GLM Code Review Bot project.

## Pipeline Structure

### Stages
1. **validate** - Code quality and pre-commit checks
2. **test** - Unit, integration, and performance tests
3. **security** - Dependency, code, and container security scanning
4. **build** - Docker image building and registry push
5. **deploy-staging** - Deployment to staging environment
6. **deploy-production** - Production deployment with blue-green strategy

### Key Features

#### Testing Pipeline
- **Multi-Python Version Support**: Tests run on Python 3.11 and 3.12
- **Comprehensive Test Coverage**: Unit, integration, and performance tests
- **Coverage Reporting**: Cobertura format with HTML and XML reports
- **Parallel Execution**: Tests run in parallel for faster feedback

#### Security Pipeline
- **Dependency Scanning**: Safety and pip-audit for known vulnerabilities
- **Code Security**: Bandit and Semgrep for static analysis
- **Container Security**: Trivy for image vulnerability scanning
- **SAST Integration**: GitLab's built-in security scanning

#### Build Pipeline
- **Docker Multi-tagging**: Tags with commit SHA, branch name, and latest
- **Registry Integration**: Pushes to GitLab Container Registry
- **Caching Optimized**: Docker layer caching for faster builds

#### Deployment Pipeline
- **Environment-Specific**: Separate configurations for staging/production
- **Blue-Green Deployment**: Zero-downtime deployments for production
- **Health Checks**: Automated health verification after deployment
- **Rollback Support**: Ability to quickly rollback to previous versions

## Configuration Files

### .gitlab-ci.yml
Main pipeline configuration with all stages and jobs.

### Docker Compose Files
- **docker-compose.yml**: Base configuration
- **docker-compose.staging.yml**: Staging environment overrides
- **docker-compose.prod.yml**: Production environment with monitoring

### Scripts
- **scripts/health-check.sh**: Container health verification
- **scripts/deploy.sh**: Deployment automation script

### Monitoring
- **monitoring/prometheus.yml**: Prometheus configuration
- **monitoring/grafana/**: Grafana dashboards and datasources

## Environment Variables

### Required
- `GLM_API_KEY`: GLM API authentication key
- `GITLAB_TOKEN`: GitLab API personal access token
- `GITLAB_API_URL`: GitLab instance API URL

### Optional
- `LOG_LEVEL`: Application logging level (default: INFO)
- `MAX_FILE_SIZE`: Maximum file size for processing
- `TOKEN_LIMIT`: Token limit for API calls
- `REVIEW_TYPE`: Type of code review to perform

### Deployment Variables
- `SSH_PRIVATE_KEY`: SSH key for server access
- `STAGING_HOST`: Staging server hostname
- `PRODUCTION_HOST`: Production server hostname
- `DEPLOY_USER`: Username for deployment

## Usage

### Merge Request Pipeline
Automatically triggered for merge requests:
- Runs validation and testing stages
- Performs security scans
- Provides comprehensive feedback

### Branch Pipeline
Triggered for `main` and `develop` branches:
- Runs full pipeline including build
- Deploys to staging for `develop` branch
- Ready for production deployment for `main` branch

### Production Deployment
- Manual trigger required for safety
- Blue-green deployment strategy
- Comprehensive health checks
- Automatic rollback on failure

## Security Considerations

### Secret Management
- All secrets stored in GitLab CI/CD variables
- Secure variable masking in logs
- Environment-specific secret isolation

### Container Security
- Non-root user in containers
- Read-only filesystem where possible
- Security scanning before deployment

### Network Security
- Isolated Docker networks
- HTTPS-only communication
- Firewall rules for services

## Performance Optimizations

### Caching
- Pip cache for Python dependencies
- Docker layer caching
- Pre-commit cache reuse

### Parallel Execution
- Multiple Python versions in parallel
- Test distribution across runners
- Concurrent security scans

### Resource Management
- CPU and memory limits defined
- Cleanup of unused resources
- Efficient image sizes

## Troubleshooting

### Common Issues
1. **Cache Misses**: Check cache key configuration
2. **Permission Errors**: Verify SSH keys and file permissions
3. **Health Check Failures**: Check service logs and connectivity
4. **Security Scan Failures**: Review vulnerability reports and update dependencies

### Debug Commands
```bash
# Check pipeline status
gitlab-ci pipeline list

# View job logs
gitlab-ci job trace <job-id>

# Manual trigger
gitlab-ci pipeline create --variables KEY=VALUE
```

## Maintenance

### Regular Updates
- Update base Docker images
- Refresh security scanning tools
- Review and update dependency versions
- Monitor and optimize pipeline performance

### Monitoring
- Track pipeline duration and success rates
- Monitor container resource usage
- Alert on deployment failures
- Review security scan results

## Future Enhancements

### Planned Improvements
- Automated dependency updates
- Canary deployments
- Advanced monitoring and alerting
- Performance benchmarking
- Compliance reporting