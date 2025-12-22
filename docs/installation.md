# Installation Guide

## Overview

This guide covers installation and setup of the GLM Code Review Bot. The bot can be installed in several ways depending on your environment and requirements.

## Prerequisites

### System Requirements

- **Python**: 3.11 or higher
- **Git**: For cloning repository
- **Access to GitLab**: With API access
- **GLM API Key**: For code analysis

### API Access

1. **GitLab Personal Access Token**
   - Go to GitLab → User Settings → Access Tokens
   - Create token with scopes: `api`, `read_repository`, `read_api`
   - Keep the token secure

2. **GLM API Key**
   - Sign up at [GLM Platform](https://z.ai)
   - Generate an API key in your account settings

## Installation Options

### Option 1: Git Clone (Recommended for Customization)

```bash
# Clone the repository
git clone https://github.com/your-org/review-bot.git
cd review-bot

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Option 2: Docker (Recommended for Production)

```bash
# Pull the image (if published)
docker pull review-bot:latest

# Or build locally
docker build -t review-bot .

# Run with an environment file
docker run --env-file .env review-bot
```

### Option 3: Direct Download

```bash
# Download the latest release
wget https://github.com/your-org/review-bot/releases/latest/download/review-bot.tar.gz
tar -xzf review-bot.tar.gz
cd review-bot

# Install dependencies
pip install -r requirements.txt
```

## Environment Setup

### 1. Create an Environment File

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` with your configuration:

```bash
# Required configuration
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GLM_API_KEY=your-glm-api-key
CI_PROJECT_ID=123
CI_MERGE_REQUEST_IID=456

# GitLab API URL (default: https://gitlab.com/api/v4)
GITLAB_API_URL=https://gitlab.com/api/v4

# GLM API URL (default: https://api.z.ai/api/paas/v4/chat/completions)
GLM_API_URL=https://api.z.ai/api/paas/v4/chat/completions

# Optional configuration
LOG_LEVEL=INFO
MAX_DIFF_SIZE=50000
ENABLE_SECURITY_REVIEW=true
ENABLE_INLINE_COMMENTS=true
```

### 2. Validate Configuration

Run the validation command:

```bash
python review_bot.py --validate-only
```

This will check all required variables and configuration.

### 3. Test Installation

Run a dry run to verify everything works:

```bash
python review_bot.py --dry-run
```

## GitLab CI/CD Integration

### 1. Add CI/CD Variables

In GitLab, go to:
Project → Settings → CI/CD → Variables

Add these variables:
- `GITLAB_TOKEN`: Your GitLab Personal Access Token
- `GLM_API_KEY`: Your GLM API Key
- Optional: Override any default settings

### 2. Add .gitlab-ci.yml

Copy the provided `.gitlab-ci.yml` to your project root:

```yaml
stages:
  - validate
  - test
  - review

workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
    - if: $CI_COMMIT_BRANCH == $CI_DEFAULT_BRANCH

code_review:
  stage: review
  image: python:3.11
  variables:
    TIMEOUT: "600"
  before_script:
    - python -m venv venv
    - source venv/bin/activate
    - pip install -r requirements.txt
  script:
    - python review_bot.py
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: manual
```

### 3. Commit and Test

1. Commit the CI/CD configuration
2. Create a test merge request
3. Manually trigger the review job
4. Verify comments appear on the MR

## Docker Setup

### 1. Build the Image

```bash
# Build locally
docker build -t review-bot .

# Or with a custom tag
docker build -t my-org/review-bot:v1.0.0 .
```

### 2. Run with Docker

```bash
# Create an environment file
echo "GITLAB_TOKEN=glpat-xxx" > .env
echo "GLM_API_KEY=your-key" >> .env

# Run the container
docker run --env-file .env review-bot
```

### 3. Docker Compose (Optional)

Create `docker-compose.yml`:

```yaml
version: '3.8'

services:
  review-bot:
    build: .
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
```

Run with:
```bash
docker-compose up -d
```

## Development Setup

### 1. Clone and Install

```bash
git clone https://github.com/your-org/review-bot.git
cd review-bot

# Create a dev environment
python -m venv venv
source venv/bin/activate

# Install with dev dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. Development Configuration

Create `.env.development`:

```bash
LOG_LEVEL=DEBUG
API_REQUEST_DELAY=0.1
MAX_DIFF_SIZE=10000
```

Load the development environment:
```bash
export $(cat .env.development | xargs)
python review_bot.py
```

### 3. Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run a specific test file
pytest tests/test_gitlab_client.py
```

### 4. Code Quality

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Cloud Deployment

### GitLab Runner

For a self-hosted GitLab Runner:

1. Install and configure GitLab Runner
2. Register the runner with your project
3. Ensure the runner has internet access for APIs
4. Configure the runner with the Docker executor

### Kubernetes

Create a Kubernetes deployment:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: review-bot
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
```

Create a secret:
```bash
kubectl create secret generic review-bot-secrets \
  --from-literal=GITLAB_TOKEN=glpat-xxx \
  --from-literal=GLM_API_KEY=your-key
```

## Verification

### 1. Check Installation

```bash
# Verify Python version
python --version

# Check installed packages
pip list | grep -E "(httpx|gitlab|structlog)"

# Test imports
python -c "import src.gitlab_client; print('OK')"
```

### 2. Test API Access

```bash
# Test GitLab token
curl -H "Authorization: Bearer $GITLAB_TOKEN" \
     "$GITLAB_API_URL/projects"

# Test GLM token (requires curl with auth)
# This will be tested by the bot's validation
```

### 3. Run End-to-End Test

```bash
# Dry run on an actual MR
python review_bot.py --dry-run

# Check output for success message
# Should show "✅ Review completed" with stats
```

## Troubleshooting

### Common Issues

#### 1. Python Version Error

```
ERROR: Python 3.11+ is required
```

Solution:
```bash
# Check your version
python --version

# Install the correct version
pyenv install 3.11.0
pyenv global 3.11.0
```

#### 2. Missing Dependencies

```
ModuleNotFoundError: No module named 'src'
ImportError: cannot import name 'gitlab_client'
```

Solutions:
```bash
# Add src to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or install in development mode
pip install -e .
```

#### 3. Authentication Error

```
GitLabAPIError: Invalid token
```

Solution:
- Verify the token has the correct scopes
- Check that the token hasn't expired
- Ensure the token is properly set in the environment

#### 4. CI/CD Variables Not Available

```
Missing required environment variables
```

Solution:
- Check variable names in the GitLab UI
- Verify variables are marked as "Protected" if needed
- Ensure variables are available for your branch

### Debug Mode

Enable debug logging:

```bash
# Set log level
export LOG_LEVEL=DEBUG

# Or use the CLI flag
python review_bot.py --log-level DEBUG
```

### Getting Help

1. Check the [Troubleshooting Guide](troubleshooting.md) for detailed solutions
2. Review the [Configuration Guide](configuration.md) for setup options
3. Open an issue in the project repository
4. Check existing issues for similar problems

## Next Steps

After successful installation:

1. Review the [Configuration Guide](configuration.md) to customize the settings
2. Check the [Usage Examples](usage.md) for practical usage scenarios
3. Read the [Architecture Documentation](architecture.md) to understand the system
4. Set up monitoring and alerting for production use

You're now ready to use the GLM Code Review Bot! 🎉