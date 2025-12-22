# API Documentation

## Overview

This document details the API integrations used by the GLM Code Review Bot, including GitLab API and GLM API interactions.

## GitLab API Integration

### Authentication

The bot uses Personal Access Token authentication with GitLab API:

```python
headers = {
    "Authorization": f"Bearer {gitlab_token}",
    "Content-Type": "application/json"
}
```

### Required Scopes

The GitLab token requires the following scopes:
- `api` - Full API access
- `read_repository` - Read repository content
- `read_api` - Read API access

### API Endpoints Used

#### 1. Get Merge Request Details

```http
GET /projects/{project_id}/merge_requests/{mr_iid}
```

**Response:**
```json
{
  "id": 123,
  "iid": 456,
  "title": "Add new feature",
  "description": "MR description",
  "source_branch": "feature-branch",
  "target_branch": "main",
  "author": {
    "id": 789,
    "name": "John Doe",
    "username": "jdoe"
  },
  "diff_refs": {
    "base_sha": "abc123...",
    "start_sha": "def456...",
    "head_sha": "ghi789..."
  }
}
```

#### 2. Get Merge Request Diffs

```http
GET /projects/{project_id}/merge_requests/{mr_iid}/diffs
```

**Response:**
```json
[
  {
    "old_path": "src/file.py",
    "new_path": "src/file.py",
    "new_file": false,
    "deleted_file": false,
    "renamed_file": false,
    "diff": "@@ -1,3 +1,4 @@\n context\n+added line\n context",
    "b_mode": "100644"
  }
]
```

#### 3. Post Merge Request Note (Comment)

```http
POST /projects/{project_id}/merge_requests/{mr_iid}/notes
```

**Request Body:**
```json
{
  "body": "Comment text with **markdown** formatting"
}
```

**Response:**
```json
{
  "id": 1001,
  "body": "Comment text",
  "author": {
    "name": "GLM Bot"
  },
  "created_at": "2023-12-21T10:30:00Z"
}
```

#### 4. Post Inline Comment

```http
POST /projects/{project_id}/merge_requests/{mr_iid}/notes
```

**Request Body:**
```json
{
  "body": "Consider using list comprehension here",
  "position": {
    "base_sha": "abc123...",
    "start_sha": "def456...",
    "head_sha": "ghi789...",
    "position_type": "text",
    "new_path": "src/file.py",
    "new_line": 42
  }
}
```

### Rate Limiting

GitLab implements rate limiting:
- **Authenticated requests**: ~1000 requests per hour
- **Burst limit**: ~100 requests per minute

The bot implements automatic rate limiting with configurable delays:
```python
self.api_request_delay = 0.5  # seconds between requests
```

### Error Handling

Common GitLab API errors and their handling:

| Status Code | Error | Handling |
|------------|-------|----------|
| 401 | Unauthorized | Re-authentication required |
| 403 | Forbidden | Insufficient permissions |
| 404 | Not Found | Invalid project/MR ID |
| 429 | Too Many Requests | Apply rate limiting |
| 500 | Internal Server Error | Retry with backoff |

## GLM API Integration

### Authentication

The bot uses Bearer token authentication with GLM API:

```python
headers = {
    "Authorization": f"Bearer {glm_api_key}",
    "Content-Type": "application/json"
}
```

### API Endpoint

```http
POST https://api.z.ai/api/paas/v4/chat/completions
```

### Request Format

```json
{
  "model": "glm-4",
  "messages": [
    {
      "role": "system",
      "content": "System prompt defining review context"
    },
    {
      "role": "user",
      "content": "Code diff to analyze"
    }
  ],
  "temperature": 0.3,
  "max_tokens": 4000,
  "stream": false
}
```

### Response Format

```json
{
  "choices": [
    {
      "index": 0,
      "message": {
        "role": "assistant",
        "content": "Analysis results in JSON or text format"
      }
    }
  ],
  "usage": {
    "prompt_tokens": 1500,
    "completion_tokens": 500,
    "total_tokens": 2000
  }
}
```

### Model Configuration

#### GLM-4 Parameters

- **temperature**: 0.3 (default)
  - Controls randomness in responses
  - Lower values for more deterministic output
  - Range: 0.0 to 1.0

- **max_tokens**: 4000 (default)
  - Maximum tokens in response
  - Includes both input and output tokens
  - Adjust based on diff size

- **model**: "glm-4" (default)
  - Primary model for code analysis
  - Optimized for code understanding
  - Supports multiple programming languages

### Prompt Engineering

#### System Prompts

The bot uses different system prompts based on review type:

1. **General Review Prompt**
```python
"""You are an expert code reviewer conducting a thorough analysis of a merge request.
Your task is to review the provided code changes and provide constructive feedback.
Focus on:
- Code quality and maintainability
- Potential bugs or issues
- Performance considerations
- Security best practices
- Code style and conventions"""
```

2. **Security Review Prompt**
```python
"""You are a senior security engineer conducting a comprehensive security code review.
Focus on:
- Authentication & Authorization
- Input Validation
- Data Protection
- Dependencies
- Configuration
- Business Logic Flaws"""
```

3. **Performance Review Prompt**
```python
"""You are a performance optimization specialist reviewing code for efficiency.
Focus on:
- Algorithmic Complexity
- Memory Usage
- I/O Operations
- Concurrency
- Resource Management
- Caching"""
```

#### User Prompt Structure

```python
user_prompt = f"""
{custom_prompt if provided else default_prompt}

Analyze the following code changes and provide feedback in JSON format:
{{
  "comments": [
    {{
      "file": "path/to/file.py",
      "line": 42,
      "comment": "Consider using list comprehension here",
      "type": "suggestion|issue|praise",
      "severity": "low|medium|high|critical"
    }}
  ]
}}

Diff to analyze:
{diff_content}
"""
```

### Token Management

#### Estimation Strategy

The bot uses multiple strategies for token estimation:

1. **tiktoken library** (preferred):
```python
import tiktoken
tokenizer = tiktoken.get_encoding("cl100k_base")
tokens = len(tokenizer.encode(text))
```

2. **Character-based fallback**:
```python
if content_type == "code":
    return len(content) * 0.25  # 1 token ≈ 4 chars
elif content_type == "diff":
    return len(content) * 0.3   # Account for diff markers
```

#### Token Limits

- **Maximum input**: ~32000 tokens (model limit)
- **Recommended usage**: 20000-25000 tokens input
- **Chunk size**: 50000 tokens (configurable)
- **Reservation**: 25% of tokens for response

### Error Handling

#### GLM API Errors

| Error Type | Description | Handling |
|------------|-------------|----------|
| Timeout | Request exceeded timeout | Retry with increased timeout |
| RateLimit | Too many requests | Exponential backoff |
| InvalidToken | Authentication failed | Re-authenticate |
| ModelOverloaded | Model at capacity | Retry with backoff |
| InvalidRequest | Bad request format | Log and skip chunk |

#### Retry Configuration

```python
@retry_with_backoff(RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    max_delay=30.0,
    backoff_factor=2.0,
    jitter=True
))
```

## Integration Patterns

### Request Flow

1. **GitLab Diff Fetch**
   - Get MR details
   - Fetch raw diffs
   - Parse and format

2. **Diff Processing**
   - Filter files
   - Estimate tokens
   - Create chunks

3. **GLM Analysis**
   - Build prompts
   - Make API calls
   - Parse responses

4. **Comment Publishing**
   - Format comments
   - Apply rate limiting
   - Post to GitLab

### Data Transformation

```python
# GitLab diff → Structured format
gitlab_diff = [
    {
        "old_path": "file.py",
        "new_path": "file.py",
        "diff": "@@ -1,3 +1,4 @@\n context\n+new line"
    }
]

# → FileDiff objects
file_diffs = [
    FileDiff(
        old_path="file.py",
        new_path="file.py",
        change_type="modified",
        hunks=["@@ -1,3 +1,4 @@", "+new line"]
    )
]

# → Diff chunks for processing
chunks = [
    DiffChunk(
        files=[file_diff],
        estimated_tokens=1500
    )
]
```

### Error Propagation

```python
try:
    # API call
    response = make_api_call()
except GLMAPIError as e:
    # Log error details
    logger.error(f"GLM API error: {e}", exc_info=True)
    
    # Convert to bot error
    raise ReviewBotError(f"Analysis failed: {e}") from e
```

## Configuration

### Environment Variables

#### GitLab Configuration
```bash
GITLAB_TOKEN="glpat-xxxxxxxxxxxxxxxxxxxx"
GITLAB_API_URL="https://gitlab.com/api/v4"
CI_PROJECT_ID="123"
CI_MERGE_REQUEST_IID="456"
```

#### GLM Configuration
```bash
GLM_API_KEY="your-glm-api-key"
GLM_API_URL="https://api.z.ai/api/paas/v4/chat/completions"
GLM_MODEL="glm-4"
GLM_TEMPERATURE="0.3"
GLM_MAX_TOKENS="4000"
```

### Rate Limiting Settings

```python
# API request delays
api_request_delay = 0.5  # seconds between requests
max_retries = 3
retry_delay = 1.0
retry_backoff_factor = 2.0

# Processing limits
max_diff_size = 50000
max_files_per_chunk = 10
```

## Best Practices

### Security

1. **Token Management**
   - Store tokens in environment variables
   - Never log or expose tokens
   - Rotate tokens regularly

2. **Input Validation**
   - Validate file paths
   - Check content length
   - Sanitize user inputs

3. **HTTPS Only**
   - All API calls over HTTPS
   - Certificate validation
   - Secure headers

### Performance

1. **Efficient Chunking**
   - Prioritize important files
   - Stay within token limits
   - Minimize API calls

2. **Rate Limiting**
   - Respect API limits
   - Implement backoff
   - Monitor usage

3. **Caching**
   - Cache token counts
   - Reuse connections
   - Batch operations

### Reliability

1. **Error Recovery**
   - Retry on failures
   - Graceful degradation
   - Circuit breakers

2. **Logging**
   - Structured logging
   - Correlation IDs
   - Error context

3. **Monitoring**
   - Track token usage
   - Measure response times
   - Alert on failures

This API documentation provides comprehensive guidance for understanding and extending the bot's integrations with GitLab and GLM APIs.