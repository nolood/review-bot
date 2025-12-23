# GLM Code Review Bot for GitLab

An automated code review bot that integrates with GitLab CI/CD to provide intelligent code analysis using the GLM-4 model. The bot analyzes merge requests and posts structured comments directly in the MR, helping developers improve code quality.

## Features

- 🔍 **Intelligent Code Analysis** - Uses GLM-4 model for comprehensive code review
- 📝 **File-Specific Comments** - Provides targeted feedback with line references
- 🚀 **GitLab CI/CD Integration** - Seamlessly integrates into your existing pipeline
- 📊 **Multi-File Support** - Handles both small and large merge requests
- 🎯 **Configurable Reviews** - Customizable review criteria and severity levels
- 🔐 **Security Focus** - Identifies potential security vulnerabilities
- ⚡ **Performance Optimized** - Efficient diff processing and chunking

## Quick Start

### 1. Prerequisites

- GitLab project with CI/CD enabled
- GitLab Personal Access Token with `api` scope
- GLM API key from [Z.ai](https://z.ai/)
- Docker and Docker Compose (for monitoring)

### 2. Setup

1. Clone this repository to your GitLab project
2. Set up the following CI/CD variables in GitLab:

   | Variable | Description | Protected | Masked |
   |----------|-------------|-----------|--------|
   | `GLM_API_KEY` | Your GLM API key | Yes | Yes |
   | `GITLAB_TOKEN` | GitLab Personal Access Token | Yes | Yes |
   | `GITLAB_API_URL` | GitLab API URL | No | No |

3. Set up monitoring environment variables:

   ```bash
   cp .env.example .env
   # Edit .env with your monitoring configuration
   ```

4. Add the following to your `.gitlab-ci.yml`:

```yaml
stages:
  - review

code_review:
  stage: review
  image: python:3.11
  variables:
    PYTHON_VERSION: "3.11"
  before_script:
    - pip install -r requirements.txt
  script:
    - python review_bot.py
  only:
    - merge_requests
  artifacts:
    paths:
      - review_logs/
    expire_in: 1 week
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

5. Start the monitoring stack:

```bash
# Development environment
docker-compose up -d

# Production environment
docker-compose -f docker-compose.prod.yml up -d
```

### 3. Monitoring Setup

The monitoring stack includes:

- **Prometheus**: http://localhost:9090 - Metrics collection
- **Grafana**: http://localhost:3000 - Data visualization
- **AlertManager**: http://localhost:9093 - Alerting
- **Node Exporter**: http://localhost:9100 - System metrics
- **cAdvisor**: http://localhost:8080 - Container metrics

See [MONITORING_STACK.md](MONITORING_STACK.md) for detailed setup instructions.

### 3. Configuration

Optional configuration via CI/CD variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GLM_TEMPERATURE` | 0.3 | GLM model creativity (0-1) |
| `MAX_DIFF_SIZE` | 50000 | Maximum diff size in tokens |
| `ENABLE_SECURITY_REVIEW` | true | Enable security analysis |
| `ENABLE_PERFORMANCE_REVIEW` | true | Enable performance analysis |
| `MIN_SEVERITY_LEVEL` | low | Minimum comment severity |

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitLab CI     │    │  Review Bot     │    │   GLM API       │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Pipeline  │ │    │ │ Diff Parser │ │    │ │   Analysis  │ │
│ │   Trigger   ├─┼───▶│ │             ├─┼───▶│ │   Engine    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Comment     │ │◀───│ │ Comment     │ │    │                 │
│ │ Publisher   │ │    │ │ Publisher   │ │    │                 │
│ └─────────────┘ │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Documentation

### User Guides
- [Installation Guide](docs/installation.md) - How to install and set up bot
- [Configuration Guide](docs/configuration.md) - How to configure bot for your project
- [Deployment Guide](docs/deployment.md) - Comprehensive production deployment instructions
- [Maintenance Procedures](docs/maintenance.md) - Ongoing maintenance and operational procedures
- [Usage Examples](docs/usage.md) - Examples of how to use bot effectively
- [Troubleshooting Guide](docs/troubleshooting.md) - Common issues and solutions
- [Monitoring Stack](MONITORING_STACK.md) - Complete monitoring and alerting setup

### Developer Documentation
- [Development Plan](docs/development_plan.md) - Detailed implementation roadmap
- [Integration Guide](docs/integration_plan.md) - Step-by-step integration instructions
- [Technical Specification](docs/technical_implementation.md) - In-depth technical details
- [API Documentation](docs/api.md) - Details about GitLab and GLM API integrations
- [Testing Infrastructure](docs/testing_infrastructure.md) - Test suite and CI/CD pipeline documentation
- [Contributing Guidelines](docs/contributing.md) - How to contribute to the project

### Project Documentation
- [Project Specification](docs/spec.md) - Original project requirements (Russian)
- [Implementation Summary](docs/implementation_summary.md) - Overview of what was built
- [Critical Fixes](docs/features/critical-fixes.md) - Comprehensive fixes and improvements
- [Changelog](docs/changelog.md) - Version history and changes
- [Roadmap](docs/roadmap.md) - Future development plans
- [Security Considerations](docs/security.md) - Security implications and best practices

## Example Output

The bot generates structured comments like this:

### 📁 src/calculator.py

💡 (line 13): Consider using type hints for better code documentation
⚠️ (line 25): Division by zero possible - add input validation
🚨 (line 42): Hardcoded credentials detected - use environment variables

### 📊 Overall Review Summary

- **Security**: 2 high-severity issues found
- **Performance**: 1 optimization opportunity identified
- **Code Quality**: 3 suggestions for improvement
- **Documentation**: 1 missing docstring detected

## File Structure

```
/
├── .gitlab-ci.yml          # CI/CD pipeline configuration
├── docker-compose.yml       # Development Docker Compose with monitoring
├── docker-compose.prod.yml   # Production Docker Compose with monitoring
├── Dockerfile             # Application container with monitoring deps
├── requirements.txt        # Python dependencies
├── review_bot.py          # Main bot script
├── test_monitoring_stack.sh # Monitoring stack validation script
├── src/
│   ├── gitlab_client.py   # GitLab API client
│   ├── glm_client.py      # GLM API client
│   ├── diff_parser.py     # Diff processing
│   └── comment_publisher.py # Comment formatting
├── monitoring/            # Monitoring configuration
│   ├── prometheus.yml     # Prometheus configuration
│   ├── alertmanager.yml   # AlertManager configuration
│   ├── rules/            # Prometheus alert rules
│   ├── grafana/          # Grafana dashboards and datasources
│   └── alertmanager_templates/ # Email templates
├── tests/                 # Test suite
├── config/                # Configuration files
└── docs/                  # Documentation
```

## Customization

### Custom Review Rules

Create a `config/review_rules.py` file to define custom rules:

```python
CUSTOM_RULES = {
    'python': {
        'naming': {
            'pattern': r'^[a-z_][a-z0-9_]*$',
            'message': 'Variable names should follow snake_case convention'
        }
    }
}
```

### Custom Prompts

Override default prompts in `config/prompts.py`:

```python
SYSTEM_PROMPT = """
You are a senior code reviewer with expertise in:
- Clean code principles
- Design patterns
- Performance optimization
- Security best practices

Focus on actionable, specific feedback.
"""
```

## Troubleshooting

### Common Issues

1. **GLM API Errors**
   - Verify your API key is correct
   - Check if you've exceeded rate limits
   - Ensure API endpoint is accessible from GitLab runners

2. **GitLab Permission Errors**
   - Verify your token has the `api` scope
   - Check if the user has sufficient permissions
   - Ensure CI/CD variables are properly configured

3. **Large Merge Requests**
   - The bot automatically chunks large diffs
   - Processing time increases with diff size
   - Consider enabling `MAX_DIFF_SIZE` limit

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=debug` in your CI/CD variables:

```yaml
variables:
  LOG_LEVEL: "debug"
```

### Monitoring Commands

```bash
# Test monitoring configuration
./test_monitoring_stack.sh

# View monitoring stack logs
docker-compose logs -f prometheus
docker-compose logs -f grafana
docker-compose logs -f alertmanager

# Scale review bot with monitoring
docker-compose up -d --scale review-bot=3

# Access monitoring dashboards
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (admin/your_password)
open http://localhost:9093  # AlertManager

# View metrics
curl http://localhost:8000/metrics  # Review Bot metrics
curl http://localhost:9100/metrics  # System metrics
curl http://localhost:8080/metrics  # Container metrics
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a merge request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in this repository
- Check the [troubleshooting guide](#troubleshooting)
- Review the [documentation](docs/)

## Roadmap

- [ ] Support for additional Git platforms (GitHub, Bitbucket)
- [ ] Web dashboard for review analytics
- [ ] Custom rule editor
- [ ] Integration with popular IDEs
- [ ] Multi-language model support

---

Made with ❤️ by the GLM Code Review Bot team