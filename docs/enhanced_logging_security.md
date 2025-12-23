# Enhanced Logging Security Implementation

## Overview

This document describes the comprehensive sensitive data redaction system implemented in the GLM Code Review Bot to prevent accidental exposure of sensitive information in logs.

## Features Implemented

### 1. Configurable Redaction Levels

- **NONE**: No redaction applied
- **BASIC**: Field name-based redaction only
- **STANDARD**: Pattern matching for common sensitive data formats (default)
- **AGGRESSIVE**: Comprehensive pattern detection with hash preservation

### 2. Comprehensive Pattern Detection

The system detects and redacts:

#### API Keys and Tokens
- `api_key="..."` patterns
- `token="..."` patterns
- `Bearer <token>` patterns
- JWT tokens (header.payload.signature)

#### Authentication Data
- Authorization headers
- Passwords and secrets
- Session tokens
- CSRF tokens

#### Database and Service Credentials
- Database URLs with passwords
- Connection strings
- Redis URLs
- AWS access keys and secret keys
- Service-specific keys (GitLab, GLM, etc.)

#### URLs and Query Parameters
- URLs with sensitive query parameters
- API endpoint URLs with keys in query string
- Database and service URLs

#### Cryptographic Data
- Hexadecimal strings (32-64 characters)
- UUIDs (potential session IDs)
- Base64 encoded data
- SHA hashes

### 3. Redaction Behavior

#### Standard Level
- Replaces sensitive data with `***REDACTED***`
- Preserves field names for debugging
- Safe default for production

#### Aggressive Level
- Replaces with hash-based placeholders: `***HASH:{short_hash}***`
- Allows tracing without exposing actual data
- Useful for debugging with more visibility

## Usage Examples

### Basic Usage

```python
from src.utils.logger import setup_logging, get_logger

# Setup with standard redaction (recommended)
setup_logging(
    sanitize_sensitive_data=True,
    redaction_level="standard"
)

# Use logger normally
logger = get_logger(__name__)
logger.info("API call with api_key='secret123'")
# Output: API call with api_key='***REDACTED***'
```

### Advanced Configuration

```python
setup_logging(
    level="DEBUG",
    format_type="json",
    sanitize_sensitive_data=True,
    redaction_level="aggressive",
    preserve_sensitive_length=False
)
```

### API Logger Usage

```python
from src.utils.logger import APILogger

api_logger = APILogger(redaction_level="standard")

# Automatic redaction of headers, URLs, and body
api_logger.log_request(
    api_name="gitlab",
    method="POST",
    url="https://gitlab.com/api/v4/projects/123/merge_requests?private_token=secret456",
    headers={
        "Authorization": "Bearer token789",
        "Content-Type": "application/json"
    },
    body={"user": "john", "password": "hidden"}
)
```

## Redaction Examples

### Before Redaction
```json
{
  "message": "API request with api_key='sk-1234567890abcdef'",
  "headers": {
    "authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "x-api-key": "live_abcdef1234567890"
  },
  "url": "https://api.example.com/data?token=secret_token_123",
  "database_url": "postgresql://user:password123@localhost:5432/db"
}
```

### After Redaction (Standard Level)
```json
{
  "message": "API request with api_key='***REDACTED***'",
  "headers": {
    "authorization": "***REDACTED***",
    "x-api-key": "***REDACTED***"
  },
  "url": "https://api.example.com/data?token=***REDACTED***",
  "database_url": "postgresql://user:***REDACTED***@localhost:5432/db"
}
```

### After Redaction (Aggressive Level)
```json
{
  "message": "API request with api_key='***HASH:1a2b3c4d***'",
  "headers": {
    "authorization": "***HASH:5e6f7a8b***",
    "x-api-key": "***HASH:9c0d1e2f***"
  },
  "url": "https://api.example.com/data?token=***HASH:3a4b5c6d***",
  "database_url": "postgresql://user:***HASH:7e8f9a0b***@localhost:5432/db"
}
```

## Security Benefits

1. **Prevents Credential Leakage**: API keys, tokens, and passwords are never written to logs
2. **Protects User Privacy**: Personal information and credentials are automatically filtered
3. **Maintains Debugging Capability**: Field names and context are preserved for troubleshooting
4. **Configurable Sensitivity**: Different levels for development vs production environments
5. **Comprehensive Coverage**: Wide range of sensitive data patterns automatically detected

## Integration with Existing Code

The redaction system integrates seamlessly with existing logging:

1. **Automatic Filtering**: All log messages pass through redaction filters
2. **Backward Compatibility**: Existing logging code continues to work unchanged
3. **Performance Optimized**: Patterns compiled once and reused efficiently
4. **Statistics Tracking**: Monitor redaction frequency and effectiveness

## Testing Coverage

The implementation includes comprehensive tests covering:

- ✅ All redaction levels and their behavior
- ✅ Pattern matching for various sensitive data types
- ✅ Dictionary and nested structure redaction
- ✅ List and tuple redaction
- ✅ API logger integration
- ✅ Filter statistics and monitoring
- ✅ Setup logging configuration
- ✅ End-to-end integration scenarios

## Best Practices

### Production Environments
```python
# Recommended production settings
setup_logging(
    sanitize_sensitive_data=True,
    redaction_level="standard",  # Safe default
    preserve_sensitive_length=False
)
```

### Development Environments
```python
# Development with more visibility
setup_logging(
    sanitize_sensitive_data=True,
    redaction_level="aggressive",  # Hash preservation
    preserve_sensitive_length=True
)
```

### When Debugging Sensitive Issues
```python
# Temporary debugging (use with caution)
setup_logging(
    sanitize_sensitive_data=False,  # Only for debugging!
    redaction_level="none"
)
```

## Configuration

### Environment Variables
The redaction system respects existing environment variables:

- `LOG_LEVEL`: Logging level
- `LOG_FORMAT`: Output format
- `LOG_FILE`: Log file path
- `LOG_SANITIZE`: Enable/disable sanitization (default: True)

### Redaction Configuration
```python
# Custom redaction level
import os
from src.utils.logger import setup_logging

redaction_level = os.getenv("LOG_REDACTION_LEVEL", "standard")
setup_logging(redaction_level=redaction_level)
```

## Performance Considerations

- **Regex Compilation**: Patterns are compiled once during initialization
- **Efficient Matching**: Optimized patterns minimize backtracking
- **Early Returns**: Fast path for non-sensitive data
- **Memory Usage**: Minimal overhead for redaction operations

## Future Enhancements

Potential improvements for future versions:

1. **Custom Patterns**: Allow users to define custom redaction patterns
2. **File Exclusions**: Skip redaction for specific log files
3. **Dynamic Levels**: Change redaction level without restart
4. **Audit Logging**: Log redactions for security auditing
5. **Machine Learning**: ML-based detection of sensitive patterns

## Security Validation

The implementation has been validated with:

- ✅ Real-world credential examples
- ✅ Various encoding formats
- ✅ Complex nested data structures
- ✅ High-volume logging scenarios
- ✅ Edge cases and malformed data
- ✅ Performance under load

This comprehensive sensitive data redaction system significantly enhances the security posture of the GLM Code Review Bot while maintaining useful logging capabilities for debugging and monitoring.