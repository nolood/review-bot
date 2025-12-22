# GLM Code Review Bot - Main Entry Point

## Overview

The `review_bot.py` script is the main entry point for the GLM-powered GitLab code review bot. It orchestrates the entire review process by integrating:

- GitLab API client for fetching MR details and diffs
- GLM client for code analysis  
- Diff parser for processing and chunking changes
- Comment publisher for structured feedback
- Comprehensive error handling and logging

## Quick Start

### 1. Setup Environment Variables

```bash
# Required variables
export GITLAB_TOKEN="your_gitlab_personal_access_token"
export GLM_API_KEY="your_glm_api_key"
export CI_PROJECT_ID="your_project_id"
export CI_MERGE_REQUEST_IID="your_mr_id"

# Optional variables (see .env.example for all options)
export GITLAB_API_URL="https://gitlab.com/api/v4"
export MAX_DIFF_SIZE="50000"
export LOG_LEVEL="INFO"
```

### 2. Basic Usage

```bash
# Run general review on current MR
python3 review_bot.py

# Run security-focused review
python3 review_bot.py --type security

# Run performance-focused review  
python3 review_bot.py --type performance

# Run with custom prompt
python3 review_bot.py --custom-prompt "Focus on error handling patterns"

# Run in dry-run mode (no comments published)
python3 review_bot.py --dry-run

# Limit processing to first 3 chunks
python3 review_bot.py --max-chunks 3
```

## Command Line Options

| Option | Type | Description |
|---------|-------|-------------|
| `--type` | `{general,security,performance}` | Review type to perform (default: general) |
| `--custom-prompt` | `string` | Custom prompt instructions for review |
| `--dry-run` | `flag` | Run analysis without publishing comments |
| `--max-chunks` | `integer` | Maximum diff chunks to process |
| `--log-level` | `{DEBUG,INFO,WARNING,ERROR,CRITICAL}` | Override logging level |
| `--log-format` | `{text,json}` | Override log format (default: text) |
| `--log-file` | `string` | Log to file instead of console |
| `--validate-only` | `flag` | Only validate environment and exit |

## Review Types

### General Review (`--type general`)
Comprehensive code review covering:
- Code quality and maintainability
- Potential bugs and issues  
- Performance considerations
- Security best practices
- Code style and conventions

### Security Review (`--type security`)
Security-focused analysis examining:
- Authentication & authorization patterns
- Input validation and sanitization
- Data protection and encryption
- Dependency vulnerabilities
- Configuration security
- Business logic flaws

### Performance Review (`--type performance`)
Performance optimization review focusing on:
- Algorithmic complexity analysis
- Memory usage patterns
- I/O operation efficiency
- Concurrency and threading
- Resource management
- Caching strategies

## Workflow

1. **Environment Validation**: Validates required settings and environment variables
2. **Client Initialization**: Sets up GitLab and GLM API clients
3. **Data Fetching**: Retrieves MR details and diff content from GitLab
4. **Diff Processing**: Parses and chunks diffs according to token limits
5. **Code Analysis**: Sends chunks to GLM for review analysis
6. **Comment Formatting**: Structures GLM responses into GitLab comments
7. **Comment Publishing**: Posts comments to GitLab (skipped in dry-run)

## Example Output

### Help Command
```bash
$ python3 review_bot.py --help
usage: review_bot.py [-h] [--type {general,security,performance}]
                     [--custom-prompt CUSTOM_PROMPT] [--dry-run]
                     [--max-chunks MAX_CHUNKS]
                     [--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}]
                     [--log-format {text,json}] [--log-file LOG_FILE]
                     [--validate-only]
```

### Dry Run Example
```bash
$ python3 review_bot.py --dry-run --type security
✅ Review completed in 0.06s
📝 Generated 0 comments
```

### Validation Example
```bash
$ python3 review_bot.py --validate-only
Environment validation completed successfully
```

## Error Handling

The bot includes comprehensive error handling for:

- **Configuration Errors**: Missing environment variables, invalid settings
- **API Errors**: GitLab/GLM API failures, rate limits, timeouts
- **Processing Errors**: Diff parsing failures, token limit exceeded
- **Publishing Errors**: Comment posting failures, permission issues

Errors are logged with detailed context and appropriate exit codes are returned.

## Logging

Structured logging with multiple formats:

- **Text Format**: Human-readable with colors for console output
- **JSON Format**: Machine-readable for log aggregation systems
- **Context Information**: Project ID, MR ID, timing, token usage

## Rate Limiting & Performance

- **API Rate Limiting**: Configurable delays between requests
- **Chunk Processing**: Large diffs are automatically split into manageable chunks
- **Retry Logic**: Exponential backoff for failed requests
- **Token Estimation**: Prevents exceeding GLM API limits

## CI/CD Integration

Designed for GitLab CI/CD with automatic environment variable injection:

```yaml
# .gitlab-ci.yml
code_review:
  stage: test
  script:
    - python3 review_bot.py --type security
  variables:
    GITLAB_TOKEN: $GITLAB_TOKEN
    GLM_API_KEY: $GLM_API_KEY
  only:
    - merge_requests
```

## Troubleshooting

### Environment Validation Failed
Ensure all required environment variables are set:
```bash
export GITLAB_TOKEN="your_token"
export GLM_API_KEY="your_key"
export CI_PROJECT_ID="123"
export CI_MERGE_REQUEST_IID="456"
```

### Import Errors
Verify dependencies are installed and `src/` directory exists:
```bash
pip3 install -r requirements.txt
ls src/
```

### API Timeouts
Increase timeout values or check network connectivity:
```bash
export TIMEOUT_SECONDS="300"
export API_REQUEST_DELAY="1.0"
```

## Development

For development and testing:

```bash
# Run tests
python3 -m pytest tests/ -v

# Test with mock data
python3 review_bot.py --dry-run --log-level DEBUG

# Validate environment only
python3 review_bot.py --validate-only
```

## File Structure

The main script integrates these components:
- `src/config/` - Configuration and prompts
- `src/gitlab_client.py` - GitLab API integration
- `src/glm_client.py` - GLM API integration  
- `src/diff_parser.py` - Diff processing and chunking
- `src/comment_publisher.py` - Comment formatting and publishing
- `src/utils/` - Logging, exceptions, retry logic