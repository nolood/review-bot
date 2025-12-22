# CI/CD Pipeline and Testing Infrastructure

This document explains the CI/CD pipeline and testing infrastructure for the GLM Code Review Bot.

## GitLab CI/CD Pipeline

The GitLab CI/CD pipeline (`.gitlab-ci.yml`) includes the following stages:

### 1. Validate Stage
- **Purpose**: Code quality checks before running tests
- **Tasks**:
  - Install dependencies
  - Run code formatting checks (black)
  - Run linting (flake8)
  - Check import sorting (isort)
- **Trigger**: Runs on merge requests
- **Artifacts**: Diff report for code formatting issues

### 2. Test Stage
- **Purpose**: Run unit and integration tests
- **Tasks**:
  - Install production and development dependencies
  - Run pytest with coverage reporting
  - Generate HTML and XML coverage reports
- **Trigger**: Runs on merge requests
- **Artifacts**: Coverage reports and test results
- **Coverage**: Tracks total test coverage

### 3. Review Stage
- **Purpose**: Execute the code review bot
- **Tasks**:
  - Install dependencies
  - Run the review bot script
  - Set timeout to prevent hanging
- **Trigger**: Manual trigger on merge requests
- **Artifacts**: Review logs
- **Dependencies**: Test stage must pass

## Testing Infrastructure

### Test Categories

#### Unit Tests
- Located in `tests/test_*.py`
- Test individual components in isolation
- Mock external API calls (GitLab, GLM)
- Use pytest fixtures for test data

#### Integration Tests
- Located in `tests/test_integration.py`
- Test end-to-end workflows
- Verify component interactions
- Test error scenarios

### Test Configuration

#### pytest.ini
- Configures pytest settings
- Sets test paths and patterns
- Configures coverage reporting
- Defines test markers

#### conftest.py
- Sets up test environment
- Configures test environment variables
- Adds src directory to Python path

#### fixtures.py
- Provides test data and mock objects
- Sample GitLab diffs and GLM responses
- Mock HTTP response objects

### Running Tests Locally

```bash
# Install dependencies
make install

# Run all tests
make test

# Run tests with coverage
pytest tests/ --cov=src --cov-report=html

# Run specific test
pytest tests/test_basic.py

# Run with verbose output
pytest -v tests/
```

## Docker Configuration

### Dockerfile
- Based on Python 3.11-slim
- Multi-stage build for efficiency
- Creates non-root user for security
- Health check endpoint

### Docker Commands

```bash
# Build Docker image
make docker-build

# Run Docker container
make docker-run
```

## Code Quality Tools

### Pre-commit Hooks
- Configured in `.pre-commit-config.yaml`
- Runs before each commit
- Includes:
  - Black (code formatting)
  - isort (import sorting)
  - flake8 (linting)
  - mypy (type checking)

### Linting and Formatting

```bash
# Run linting
make lint

# Format code
make format

# Install pre-commit hooks
pre-commit install
```

## Environment Variables

### Required for CI/CD
- `GLM_API_KEY`: API key for GLM model
- `GITLAB_TOKEN`: GitLab personal access token
- `CI_PROJECT_ID`: GitLab project ID (auto-provided)
- `CI_MERGE_REQUEST_IID`: MR ID (auto-provided)

### Configuration Options
- `MAX_DIFF_SIZE`: Maximum diff size in tokens
- `ENABLE_SECURITY_REVIEW`: Enable security-focused review
- `MIN_SEVERITY_LEVEL`: Minimum comment severity
- `API_REQUEST_DELAY`: Delay between API requests

## Security Considerations

### Protected Variables
- API keys are marked as "Protected" in GitLab
- Variables are masked to prevent exposure
- Access limited to protected branches

### Container Security
- Non-root user in Docker container
- Minimal dependencies
- No shell access in production

## Monitoring and Logging

### Artifacts
- Review logs preserved for 1 week
- Coverage reports available for viewing
- Test results archived

### Log Format
- Structured JSON logging
- Request/response logging
- Error tracking

## Troubleshooting

### Common Issues

1. **Pipeline Timeouts**
   - Check diff size limits
   - Verify API accessibility
   - Review timeout settings

2. **Test Failures**
   - Check environment variables
   - Verify mock responses
   - Review test fixtures

3. **Build Failures**
   - Check dependency versions
   - Verify Python version
   - Review Docker configuration

### Debug Commands

```bash
# Run with debug logging
CI_DEBUG_TRACE=true python review_bot.py

# Check API connectivity
curl -H "Authorization: Bearer $GITLAB_TOKEN" $GITLAB_API_URL/user

# Validate configuration
python -c "from src.config.settings import Settings; Settings()"
```

## Performance Optimization

### Parallel Test Execution
```bash
pytest -n auto tests/
```

### Selective Test Runs
```bash
# Run only unit tests
pytest -m unit tests/

# Run only integration tests
pytest -m integration tests/
```

## Continuous Improvement

### Metrics to Track
- Test coverage percentage
- Pipeline execution time
- Review comment quality
- API error rates

### Regular Updates
- Update dependencies monthly
- Review test coverage quarterly
- Audit security settings annually