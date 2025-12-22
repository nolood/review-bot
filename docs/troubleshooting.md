# Troubleshooting Guide

## Overview

This guide covers common issues, error messages, and solutions when using the GLM Code Review Bot. It's organized by category for easy navigation.

## Quick Checklist

Before diving into specific issues, check these common problems:

1. **Environment Variables**
   - [ ] All required variables are set
   - [ ] Tokens are valid and not expired
   - [ ] CI/CD variables are properly configured

2. **Network Access**
   - [ ] Can reach GitLab API
   - [ ] Can reach GLM API
   - [ ] Firewall/proxy not blocking requests

3. **Permissions**
   - [ ] GitLab token has required scopes
   - [ ] User has permission to access project
   - [ ] MR is accessible to the token user

## Installation Issues

### Python Version Error

**Error:**
```
ERROR: Python 3.11+ is required
```

**Solution:**
```bash
# Check current version
python --version

# Install correct version using pyenv
pyenv install 3.11.0
pyenv global 3.11.0

# Or use system package manager
sudo apt update
sudo apt install python3.11 python3.11-venv
```

### Module Not Found

**Error:**
```
ModuleNotFoundError: No module named 'src'
ImportError: cannot import name 'gitlab_client'
```

**Solutions:**

1. **Add to Python Path:**
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
python review_bot.py
```

2. **Install in Development Mode:**
```bash
pip install -e .
```

3. **Run from Correct Directory:**
```bash
cd /path/to/review-bot
python review_bot.py
```

### Dependency Installation Fails

**Error:**
```
ERROR: Could not install packages due to EnvironmentError
Failed building wheel for tiktoken
```

**Solution:**
```bash
# Upgrade pip and setuptools
pip install --upgrade pip setuptools wheel

# Install system dependencies (Ubuntu/Debian)
sudo apt install python3-dev build-essential

# Try different index
pip install -i https://pypi.org/simple/ -r requirements.txt
```

## Authentication Issues

### GitLab Token Invalid

**Error:**
```
GitLabAPIError: 401 Unauthorized
GitLabAPIError: Invalid token
```

**Solutions:**

1. **Check Token Format:**
```bash
# Token should start with 'glpat-'
echo $GITLAB_TOKEN | head -c 6
```

2. **Verify Token Scopes:**
   - Go to GitLab → User Settings → Access Tokens
   - Ensure token has: `api`, `read_repository`, `read_api`
   - Regenerate token if needed

3. **Check Token Expiration:**
   - Tokens expire after configurable time
   - Regenerate if expired

### GLM API Key Invalid

**Error:**
```
GLMAPIError: Invalid authentication credentials
GLMAPIError: 401 Unauthorized
```

**Solutions:**

1. **Verify Key Format:**
```bash
# Check key is set
echo $GLM_API_KEY | wc -c
```

2. **Regenerate API Key:**
   - Go to GLM Platform dashboard
   - Generate new API key
   - Update environment variables

3. **Check API URL:**
```bash
# Verify correct endpoint
echo $GLM_API_URL
# Should be: https://api.z.ai/api/paas/v4/chat/completions
```

### CI/CD Variables Not Available

**Error:**
```
Missing required environment variables: GITLAB_TOKEN
ConfigurationError: GLM_API_KEY environment variable is required
```

**Solutions:**

1. **Check Variable Names:**
   - Exact case matters
   - No extra spaces or characters
   - Use underscores, not hyphens

2. **Variable Scope:**
   - Protected variables only available on protected branches
   - Masked variables not available for forks
   - Check "Environment scope" in GitLab UI

3. **Debug Variables:**
```yaml
# .gitlab-ci.yml
debug_vars:
  stage: validate
  script:
    - echo "GITLAB_TOKEN length: ${#GITLAB_TOKEN}"
    - echo "GLM_API_KEY length: ${#GLM_API_KEY}"
```

## API Issues

### Rate Limiting

**Error:**
```
GitLabAPIError: 429 Too Many Requests
GLMAPIError: Rate limit exceeded
```

**Solutions:**

1. **Increase Delays:**
```bash
# Environment variables
export API_REQUEST_DELAY=2.0
export RETRY_DELAY=5.0

# Or in .env
API_REQUEST_DELAY=2.0
RETRY_DELAY=5.0
```

2. **Reduce Parallel Requests:**
```bash
export MAX_PARALLEL_REQUESTS=1
```

3. **Process Smaller Chunks:**
```bash
python review_bot.py --max-chunks 2
```

### Timeouts

**Error:**
```
GLMAPIError: Request timeout after 60s
GitLabAPIError: Read timed out
```

**Solutions:**

1. **Increase Timeouts:**
```bash
# In .env
TIMEOUT_SECONDS=600
GLM_TIMEOUT=120

# Or as CLI argument
python review_bot.py --timeout 600
```

2. **Reduce Processing:**
```bash
# Smaller chunks
export MAX_DIFF_SIZE=25000
python review_bot.py --max-chunks 1
```

3. **Network Optimization:**
```bash
# Check network connectivity
curl -I https://api.z.ai
curl -I https://gitlab.com

# Use proxy if needed
export HTTPS_PROXY=https://proxy.company.com:8080
```

### SSL Certificate Errors

**Error:**
```
SSLError: [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed
HTTPSConnectionPool: SSLError(SSLCertVerificationError)
```

**Solutions:**

1. **Update Certificates:**
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ca-certificates

# macOS
brew update && brew install ca-certificates
```

2. **Bypass Verification (Not Recommended for Production):**
```bash
# Only for development/testing
export SSL_VERIFY=false
export GITLAB_SSL_VERIFY=false
```

3. **Use Custom Certificates:**
```bash
export SSL_CERT_FILE=/path/to/cert.pem
export REQUESTS_CA_BUNDLE=/path/to/cert.pem
```

## Processing Issues

### Large Diff Handling

**Error:**
```
TokenLimitError: File exceeds maximum token limit
DiffParsingError: Diff too large to process
```

**Solutions:**

1. **Reduce Chunk Size:**
```bash
# In .env
MAX_DIFF_SIZE=25000

# Or via CLI
python review_bot.py --max-chunks 3
```

2. **Filter More Files:**
```bash
# Add more patterns to ignore
IGNORE_FILE_PATTERNS="*.min.js,*.bundle.js,*.generated.*,*.pb.go"
```

3. **Process Specific Files:**
```bash
# Only process priority files
PRIORITIZE_FILE_PATTERNS="*.py,*.js"
export FILTER_PRIORITY_ONLY=true
```

### Memory Issues

**Error:**
```
MemoryError: Unable to allocate array
Killed
```

**Solutions:**

1. **Reduce Memory Usage:**
```bash
# Smaller chunks
export MAX_DIFF_SIZE=10000

# Limit parallel processing
export MAX_PARALLEL_REQUESTS=1
```

2. **Increase System Memory:**
```bash
# Docker
docker run --memory=1g review-bot

# System limits
ulimit -v 1048576  # 1GB limit
```

3. **Use Stream Processing:**
```bash
# Process in streaming mode
python review_bot.py --stream-chunks
```

### File Parsing Errors

**Error:**
```
DiffParsingError: Invalid diff format
TypeError: expected string, got bytes
```

**Solutions:**

1. **Check Diff Encoding:**
```bash
# Ensure UTF-8 encoding
export LC_ALL=C.UTF-8
export LANG=C.UTF-8
```

2. **Handle Binary Files:**
```bash
# Skip binary files automatically
export SKIP_BINARY_FILES=true
```

3. **Debug Diff Content:**
```bash
# Save diff for inspection
python review_bot.py --debug-diff --save-diff /tmp/debug.diff
```

## CI/CD Issues

### Pipeline Not Triggering

**Symptom:**
- Review bot job doesn't appear in pipeline
- Job appears but doesn't run

**Solutions:**

1. **Check Pipeline Rules:**
```yaml
# Ensure correct rule
workflow:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
```

2. **Verify Branch Configuration:**
```yaml
# Only run on MRs
code_review:
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: manual
```

3. **Check Protected Branches:**
   - Manual triggers required for protected branches
   - Variables may not be available for forks

### Job Fails Silently

**Symptom:**
- Job appears to succeed but no comments posted
- Exit code 0 but no output

**Solutions:**

1. **Enable Debug Logging:**
```yaml
variables:
  LOG_LEVEL: DEBUG
  LOG_FORMAT: json
```

2. **Check Job Logs:**
```bash
# Download artifacts
wget https://gitlab.com/project/-/jobs/12345/artifacts/download

# Check review logs
cat review_logs/review_bot.log | grep ERROR
```

3. **Validate Environment:**
```yaml
# Add validation step
validate:
  script:
    - python review_bot.py --validate-only
```

### Docker Issues

**Error:**
```
Error: No such image: review-bot:latest
docker: Error response from daemon: pull access denied
```

**Solutions:**

1. **Build Image Locally:**
```bash
# Build before running
docker build -t review-bot .
docker run --env-file .env review-bot
```

2. **Check Dockerfile:**
```dockerfile
# Ensure correct FROM line
FROM python:3.11-slim

# Verify working directory
WORKDIR /app
```

3. **Debug Container:**
```bash
# Interactive debugging
docker run -it --entrypoint /bin/bash review-bot
```

## Performance Issues

### Slow Processing

**Symptom:**
- Reviews taking too long to complete
- Pipelines timing out

**Solutions:**

1. **Optimize Configuration:**
```bash
# Increase parallelism
export MAX_PARALLEL_REQUESTS=3

# Reduce unnecessary processing
export MIN_SEVERITY_LEVEL=high
```

2. **Profile Performance:**
```bash
# Enable performance logging
export PROFILE_PERFORMANCE=true
python review_bot.py
```

3. **Cache Dependencies:**
```yaml
# .gitlab-ci.yml
cache:
  paths:
    - .cache/pip
    - .cache/tiktoken
```

### High Token Usage

**Symptom:**
- Exceeding GLM token limits
- High API costs

**Solutions:**

1. **Reduce Input Size:**
```bash
# Smaller chunks
export MAX_DIFF_SIZE=15000

# Filter aggressively
IGNORE_FILE_PATTERNS="*.min.*,*.generated.*,*test*"
```

2. **Monitor Usage:**
```bash
# Enable token tracking
export TRACK_TOKEN_USAGE=true
python review_bot.py
```

3. **Optimize Prompts:**
```bash
# Use focused prompts
python review_bot.py --custom-prompt "Only check for security issues"
```

## Debugging Techniques

### Enable Debug Mode

```bash
# Full debug output
export LOG_LEVEL=DEBUG
export LOG_FORMAT=json
python review_bot.py
```

### Save Intermediate Data

```bash
# Save diff for inspection
export SAVE_DIFF=true
export DEBUG_DIR=/tmp/review_debug
python review_bot.py

# Analyze saved files
ls -la /tmp/review_debug
cat /tmp/review_debug/diff_1.json
```

### Network Debugging

```bash
# Test API connectivity
curl -H "Authorization: Bearer $GITLAB_TOKEN" \
     "$GITLAB_API_URL/projects"

# Test GLM API
curl -H "Authorization: Bearer $GLM_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"model":"glm-4","messages":[{"role":"user","content":"test"}]}' \
     "$GLM_API_URL"
```

### Component Isolation

Test individual components:

```bash
# Test GitLab client only
python -m src.gitlab_client

# Test GLM client only
python -m src.glm_client --test

# Test diff parser only
python -m src.diff_parser --test-input file.diff
```

## Getting Help

### Log Analysis

1. **Extract Errors:**
```bash
grep ERROR review_bot.log | tail -20
```

2. **Check API Response Times:**
```bash
grep "API response" review_bot.log | jq '.response_time'
```

3. **Track Token Usage:**
```bash
grep "token_usage" review_bot.log | jq '.total_tokens'
```

### Community Resources

1. **Check Existing Issues:**
   - Browse GitLab issues for similar problems
   - Check closed issues for resolved problems

2. **Create Detailed Issue Report:**
   - Include full error message
   - Provide configuration details
   - Attach relevant logs
   - Specify environment (Docker, CI/CD, local)

3. **Monitor Project Updates:**
   - Watch for bug fixes and improvements
   - Review release notes for known issues

This troubleshooting guide covers the most common issues and their solutions. For additional help, refer to the project's issue tracker or documentation.