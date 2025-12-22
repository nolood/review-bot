# Usage Examples

## Overview

This guide provides practical examples of using the GLM Code Review Bot in various scenarios. It covers command-line usage, CI/CD integration, and advanced configurations.

## Basic Usage

### Running General Review

The most common usage is a general code review:

```bash
# Run general review on current merge request
python review_bot.py

# With verbose logging
python review_bot.py --log-level DEBUG
```

Output:
```
✅ Review completed in 12.34s
📝 Generated 15 comments
📤 Published 15 comments
```

### Security-Focused Review

For security-sensitive changes:

```bash
# Run security review
python review_bot.py --type security

# Security review with specific focus
python review_bot.py --type security --custom-prompt "Focus on authentication and authorization"
```

### Performance Review

For performance-critical changes:

```bash
# Run performance review
python review_bot.py --type performance

# Performance with custom focus
python review_bot.py --type performance --custom-prompt "Focus on database query optimization"
```

## Advanced Scenarios

### Dry Run Testing

Test without publishing comments:

```bash
# Dry run to see what would be reviewed
python review_bot.py --dry-run

# Dry run with specific review type
python review_bot.py --dry-run --type security

# Dry run with custom logging
python review_bot.py --dry-run --log-file review-dryrun.log
```

### Processing Limits

Control how much is processed:

```bash
# Limit to first 3 chunks (useful for large MRs)
python review_bot.py --max-chunks 3

# Combine with other options
python review_bot.py --type security --max-chunks 2 --dry-run
```

### Custom Prompts

Define specific review criteria:

```bash
# Focus on error handling
python review_bot.py --custom-prompt "Focus specifically on error handling patterns and exception safety"

# Multiple criteria
python review_bot.py --custom-prompt "Check for: 1) Input validation 2) SQL injection risks 3) Proper logging"

# Review specific aspects
python review_bot.py --custom-prompt "Review for accessibility compliance and WCAG standards"
```

## CI/CD Integration

### Manual Trigger

Use manual trigger for control:

```yaml
# .gitlab-ci.yml
code_review:
  stage: review
  script:
    - python review_bot.py --type security
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
      when: manual
  allow_failure: true
```

### Automatic Trigger

Automatically run on all MRs:

```yaml
# .gitlab-ci.yml
code_review:
  stage: review
  script:
    - python review_bot.py --log-level INFO --log-format json
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  artifacts:
    reports:
      junit: review-results.xml
```

### Conditional Reviews

Run different reviews based on changes:

```yaml
# .gitlab-ci.yml
variables:
  # Detect if backend files changed
  BACKEND_CHANGES: 'git diff --name-only $CI_MERGE_REQUEST_DIFF_BASE_SHA $CI_COMMIT_SHA | grep -E "\.(py|java|go)$" || echo "false"'

stages:
  - validate
  - review

general_review:
  stage: review
  script:
    - python review_bot.py
  rules:
    - if: '$BACKEND_CHANGES == "true"'

security_review:
  stage: review
  script:
    - python review_bot.py --type security --dry-run
  rules:
    - if: '$BACKEND_CHANGES == "true" && $CI_MERGE_REQUEST_TITLE =~ /security/i'
```

## Configuration Examples

### Project-Specific Config

Create project-specific configuration:

```bash
# .env.project
# For web frontend project
PRIORITIZE_FILE_PATTERNS="*.js,*.ts,*.jsx,*.tsx,*.css,*.html"
IGNORE_FILE_PATTERNS="*.min.js,*.min.css,*.bundle.js,*.css.map"
MAX_DIFF_SIZE=30000
ENABLE_INLINE_COMMENTS=true
```

Load with:
```bash
export $(cat .env.project | xargs)
python review_bot.py
```

### Team-Specific Settings

Different settings for different teams:

```bash
# .env.security-team
ENABLE_SECURITY_REVIEW=true
MIN_SEVERITY_LEVEL="medium"
LOG_LEVEL="DEBUG"

# .env.performance-team
ENABLE_PERFORMANCE_REVIEW=true
MIN_SEVERITY_LEVEL="high"
API_REQUEST_DELAY=1.0
```

### Environment-Specific Config

Different settings per environment:

```bash
# Production
LOG_LEVEL="INFO"
MAX_RETRIES=3
TIMEOUT_SECONDS=300

# Development
LOG_LEVEL="DEBUG"
MAX_RETRIES=1
TIMEOUT_SECONDS=60
```

## Use Case Examples

### 1. Security Audit

For security audit of critical changes:

```bash
# Comprehensive security review
python review_bot.py \
  --type security \
  --custom-prompt "Focus on: authentication bypasses, privilege escalation, data exposure" \
  --max-chunks 10 \
  --log-level DEBUG \
  --log-file security-audit.log
```

### 2. Performance Optimization

For performance-critical changes:

```bash
# Performance review with specific focus
python review_bot.py \
  --type performance \
  --custom-prompt "Analyze for: N+1 queries, missing indexes, inefficient algorithms" \
  --dry-run \
  --log-format json
```

### 3. Code Quality Gate

Use as code quality gate in CI:

```yaml
# .gitlab-ci.yml
code_quality_gate:
  stage: test
  script:
    - python review_bot.py --min-severity medium --dry-run
    - |
      if [ $? -ne 0 ]; then
        echo "Code quality check failed"
        exit 1
      fi
```

### 4. Learning and Training

For team learning:

```bash
# Review with educational focus
python review_bot.py \
  --custom-prompt "Provide educational feedback explaining why issues matter and best practices" \
  --max-chunks 2
```

### 5. Documentation Review

For documentation changes:

```bash
# Review documentation
python review_bot.py \
  --custom-prompt "Review for: clarity, accuracy, completeness, proper formatting" \
  --dry-run
```

## Integration Examples

### With Pre-commit Hooks

```bash
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: local-review
        name: GLM Code Review
        entry: python review_bot.py --dry-run
        language: system
        pass_filenames: false
        always_run: true
```

### With API Calls

Programmatic usage:

```python
# example_script.py
import subprocess
import sys

def run_review(review_type="general", custom_prompt=None):
    """Run code review programmatically."""
    cmd = ["python", "review_bot.py"]
    
    if review_type != "general":
        cmd.extend(["--type", review_type])
    
    if custom_prompt:
        cmd.extend(["--custom-prompt", custom_prompt])
    
    # Run with dry-run to get results
    cmd.append("--dry-run")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("Review completed successfully")
        return result.stdout
    else:
        print(f"Review failed: {result.stderr}")
        return None

# Usage
if __name__ == "__main__":
    output = run_review("security", "Focus on injection vulnerabilities")
    if output:
        print(f"Found {output.count('comments')} issues")
```

### With Webhook Integration

For webhook-based triggering:

```python
# webhook_handler.py
from flask import Flask, request, jsonify
import subprocess

app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def handle_webhook():
    """Handle GitLab webhook for triggering reviews."""
    data = request.json
    
    if data.get('object_kind') == 'merge_request':
        # Extract MR details
        mr_iid = data['object_attributes']['iid']
        project_id = data['object_attributes']['source_project_id']
        
        # Trigger review
        try:
            subprocess.run([
                'python', 'review_bot.py',
                '--project-id', str(project_id),
                '--mr-iid', str(mr_iid)
            ], check=True)
            
            return jsonify({'status': 'success'})
        except subprocess.CalledProcessError as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    return jsonify({'status': 'ignored'})

if __name__ == '__main__':
    app.run(port=5000)
```

## Troubleshooting Examples

### Debugging Large MRs

For large merge requests causing timeouts:

```bash
# Process in smaller chunks
python review_bot.py --max-chunks 2 --log-level DEBUG

# Adjust configuration
export MAX_DIFF_SIZE=25000
export API_REQUEST_DELAY=1.0
python review_bot.py
```

### Investigating Issues

For detailed investigation:

```bash
# Full debug with log file
python review_bot.py \
  --log-level DEBUG \
  --log-file investigation.log \
  --dry-run \
  --type security

# Analyze log file
tail -f investigation.log | grep ERROR
```

### Testing Custom Prompts

Test custom prompts safely:

```bash
# Test with small changes first
python review_bot.py \
  --max-chunks 1 \
  --custom-prompt "Your new prompt here" \
  --dry-run

# Review output before enabling
cat review-dryrun.log | grep -A5 -B5 "comment"
```

## Best Practices

### 1. Review Type Selection

Choose appropriate review type:
- **General**: Most MRs, balanced feedback
- **Security**: Security-sensitive code, authentication, data handling
- **Performance**: Performance-critical paths, algorithms, database queries

### 2. Custom Prompts

Effective custom prompts:
- Be specific about focus areas
- Use numbered lists for clarity
- Include examples of what to look for
- Keep prompts concise yet comprehensive

### 3. Resource Management

Manage resources effectively:
- Use `--max-chunks` for large MRs
- Adjust `MAX_DIFF_SIZE` based on project needs
- Monitor token usage with debug logging

### 4. Team Integration

Integrate with team workflows:
- Use manual trigger for control in production
- Enable automatic reviews for non-critical paths
- Review bot comments in team meetings

### 5. Continuous Improvement

Improve over time:
- Monitor feedback quality
- Adjust file patterns for your codebase
- Update custom prompts based on team feedback
- Track metrics on review effectiveness

These examples demonstrate the flexibility and power of the GLM Code Review Bot across various use cases and scenarios.