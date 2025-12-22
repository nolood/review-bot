# Configuration Guide

## Overview

The GLM Code Review Bot is highly configurable through environment variables and configuration files. This guide covers all available configuration options and how to customize them for your project.

## Required Configuration

### Environment Variables

Create a `.env` file in your project root with these required variables:

```bash
# GitLab Configuration
GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"  # GitLab Personal Access Token
GITLAB_API_URL="https://gitlab.com/api/v4"   # GitLab API URL

# GLM Configuration
GLM_API_KEY="your-glm-api-key"            # GLM API Key
GLM_API_URL="https://api.z.ai/api/paas/v4/chat/completions"  # GLM API URL

# Project Context (auto-provided by GitLab CI)
CI_PROJECT_ID="123"                         # GitLab Project ID
CI_MERGE_REQUEST_IID="456"                  # Merge Request IID
```

### GitLab Personal Access Token

1. Go to GitLab → User Settings → Access Tokens
2. Create a new token with these scopes:
   - `api` - Full API access
   - `read_repository` - Read repository content
   - `read_api` - Read API access
3. Copy the token and add to `.env` file

### GLM API Key

1. Sign up at [GLM Platform](https://z.ai)
2. Generate an API key
3. Add the key to your `.env` file

## Optional Configuration

### Review Settings

```bash
# Review Types
ENABLE_SECURITY_REVIEW=true      # Enable security-focused reviews
ENABLE_PERFORMANCE_REVIEW=true   # Enable performance-focused reviews
MIN_SEVERITY_LEVEL="low"        # Minimum severity for comments (low/medium/high)

# Processing Configuration
MAX_DIFF_SIZE=50000            # Maximum diff size in tokens
MAX_FILES_PER_COMMENT=10        # Maximum files per comment batch
ENABLE_INLINE_COMMENTS=true     # Enable line-specific comments
```

### API Behavior

```bash
# Rate Limiting
API_REQUEST_DELAY=0.5           # Seconds between API requests
MAX_PARALLEL_REQUESTS=3         # Maximum parallel API calls

# Retry Configuration
MAX_RETRIES=3                   # Maximum retry attempts
RETRY_DELAY=1.0                 # Initial retry delay (seconds)
RETRY_BACKOFF_FACTOR=2.0        # Retry backoff multiplier
```

### GLM Model Settings

```bash
# GLM Model Configuration
GLM_MODEL="glm-4"              # Model name (glm-4, glm-4-plus, etc.)
GLM_TEMPERATURE=0.3             # Response randomness (0.0-1.0)
GLM_MAX_TOKENS=4000             # Maximum tokens in response
```

### File Filtering

```bash
# File Patterns to Ignore
IGNORE_FILE_PATTERNS="*.min.js,*.min.css,*.css.map,*.js.map,package-lock.json,yarn.lock,*.png,*.jpg,*.jpeg,*.gif,*.pdf,*.zip"

# File Patterns to Prioritize
PRIORITIZE_FILE_PATTERNS="*.py,*.js,*.ts,*.jsx,*.tsx,*.java,*.go,*.rs,*.cpp,*.c,*.h"
```

### Logging Configuration

```bash
# Logging Settings
LOG_LEVEL="INFO"                # Log level (DEBUG/INFO/WARNING/ERROR)
LOG_FORMAT="json"                # Log format (json/text)
LOG_FILE="/tmp/review_bot.log"   # Optional log file path
```

### Performance Settings

```bash
# Resource Limits
MEMORY_LIMIT_MB=512              # Memory limit in MB
TIMEOUT_SECONDS=300              # Request timeout in seconds
```

## Configuration Files

### Using .env File

Create a `.env` file in your project root:

```bash
# .env
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GLM_API_KEY=your-glm-api-key
CI_PROJECT_ID=123
CI_MERGE_REQUEST_IID=456

# Optional settings
LOG_LEVEL=DEBUG
MAX_DIFF_SIZE=75000
ENABLE_SECURITY_REVIEW=true
```

### GitLab CI/CD Variables

For GitLab CI/CD, set variables in:
- Project → Settings → CI/CD → Variables

```yaml
# .gitlab-ci.yml
variables:
  # These will be injected from CI/CD variables
  # GITLAB_TOKEN: $GITLAB_TOKEN
  # GLM_API_KEY: $GLM_API_KEY
  # CI_PROJECT_ID: $CI_PROJECT_ID
  # CI_MERGE_REQUEST_IID: $CI_MERGE_REQUEST_IID
```

## Review Type Configuration

### General Review

Default review type covering all aspects:
- Code quality and maintainability
- Potential bugs or issues
- Performance considerations
- Security best practices
- Code style and conventions

### Security Review

Focus on security vulnerabilities:
- Authentication & Authorization
- Input Validation
- Data Protection
- Dependencies
- Configuration

### Performance Review

Focus on optimization:
- Algorithmic Complexity
- Memory Usage
- I/O Operations
- Concurrency
- Resource Management

### Custom Prompts

Define custom review criteria:

```bash
# Command line
python review_bot.py --custom-prompt "Focus on error handling and test coverage"
```

Or set as environment variable:
```bash
CUSTOM_REVIEW_PROMPT="Focus on error handling and test coverage"
```

## File Pattern Configuration

### Ignore Patterns

Files matching these patterns are skipped during review:

```python
ignore_file_patterns = [
    "*.min.js",      # Minified JavaScript
    "*.min.css",     # Minified CSS
    "*.css.map",     # CSS source maps
    "*.js.map",      # JavaScript source maps
    "package-lock.json",  # NPM lock files
    "yarn.lock",     # Yarn lock files
    "*.png",         # Image files
    "*.jpg",         # Image files
    "*.jpeg",        # Image files
    "*.gif",         # Image files
    "*.pdf",         # PDF files
    "*.zip"          # Zip archives
]
```

### Prioritize Patterns

Files matching these patterns are reviewed first:

```python
prioritize_file_patterns = [
    "*.py",          # Python
    "*.js",          # JavaScript
    "*.ts",          # TypeScript
    "*.jsx",         # React JSX
    "*.tsx",         # React TypeScript
    "*.java",        # Java
    "*.go",          # Go
    "*.rs",          # Rust
    "*.cpp",         # C++
    "*.c",           # C
    "*.h"            # Header files
]
```

## Advanced Configuration

### Custom Settings Class

For complex configurations, extend the Settings class:

```python
# src/config/custom_settings.py
from .settings import Settings

@dataclass
class CustomSettings(Settings):
    """Extended settings for project-specific configuration."""
    
    # Custom project settings
    project_name: str = field(default="my-project")
    team_contact: str = field(default="team@example.com")
    
    # Custom review rules
    require_test_coverage: bool = field(default=True)
    max_function_length: int = field(default=50)
```

### Environment-Specific Configs

Create separate configs for different environments:

```python
# src/config/production.py
from .settings import Settings

class ProductionSettings(Settings):
    log_level = "INFO"
    max_diff_size = 50000
    api_request_delay = 1.0

# src/config/development.py
class DevelopmentSettings(Settings):
    log_level = "DEBUG"
    max_diff_size = 25000
    api_request_delay = 0.25
```

## Configuration Validation

### Required Variables Check

The bot validates all required variables on startup:

```python
# These must be set
required_vars = [
    "GITLAB_TOKEN",
    "GLM_API_KEY",
    "CI_PROJECT_ID",
    "CI_MERGE_REQUEST_IID"
]
```

### Range Validation

Numeric values are validated:

```python
# Temperature must be between 0.0 and 1.0
if not 0.0 <= settings.glm_temperature <= 1.0:
    raise ValueError("glm_temperature must be between 0.0 and 1.0")

# Log level must be valid
valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
if settings.log_level not in valid_levels:
    raise ValueError(f"Invalid log level: {settings.log_level}")
```

### URL Validation

API URLs are validated:

```python
if not settings.gitlab_api_url.startswith(("http://", "https://")):
    raise ValueError("GitLab API URL must start with http:// or https://")
```

## Best Practices

### Security

1. **Never commit secrets**: Use `.env` file and add to `.gitignore`
2. **Use CI/CD variables**: Store secrets in GitLab CI/CD variables
3. **Rotate tokens regularly**: Update API keys periodically
4. **Principle of least privilege**: Use minimal token scopes

### Performance

1. **Adjust chunk size**: Balance between API calls and token limits
2. **Tune rate limiting**: Respect API limits while maintaining speed
3. **Filter wisely**: Ignore irrelevant files to reduce processing
4. **Monitor usage**: Track token consumption and costs

### Maintainability

1. **Document changes**: Keep configuration documentation updated
2. **Use defaults**: Provide sensible defaults for optional settings
3. **Validate early**: Catch configuration errors before processing
4. **Version control**: Track configuration changes in Git

## Troubleshooting

### Common Issues

1. **Authentication errors**:
   - Check API tokens are correct
   - Verify token scopes
   - Ensure tokens haven't expired

2. **Missing environment variables**:
   - Create `.env` file from `.env.example`
   - Set CI/CD variables in GitLab
   - Check variable names match exactly

3. **Rate limiting**:
   - Increase API request delay
   - Reduce parallel requests
   - Monitor API usage

4. **Token limit errors**:
   - Reduce MAX_DIFF_SIZE
   - Improve file filtering
   - Check for binary files

### Debug Mode

Enable debug logging to troubleshoot:

```bash
# Environment variable
LOG_LEVEL=DEBUG

# Command line
python review_bot.py --log-level DEBUG
```

This configuration guide covers all aspects of customizing the GLM Code Review Bot for your project needs.