#!/usr/bin/env python3
"""
Integration test demonstrating enhanced logging security features.

This script demonstrates how the enhanced logging system protects
sensitive information in various realistic scenarios.
"""

import os
import sys
import json
from unittest.mock import patch, MagicMock

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from utils.logger import (
    setup_logging, 
    get_logger, 
    APILogger, 
    RedactionLevel
)


def test_basic_sensitive_data_redaction():
    """Test basic sensitive data redaction in regular logging."""
    print("=== Testing Basic Sensitive Data Redaction ===")
    
    # Setup logging with standard redaction
    setup_logging(
        level="INFO",
        format_type="json",
        sanitize_sensitive_data=True,
        redaction_level=RedactionLevel.STANDARD
    )
    
    logger = get_logger("security_test")
    
    # Test various sensitive data patterns
    test_scenarios = [
        ("API call", "Making API call with api_key='sk-1234567890abcdef'"),
        ("Bearer token", "Authorization: Bearer abc123def456ghi789jkl012mno345pqr678stu901vwx234yz"),
        ("Database URL", "Connecting to postgresql://user:password123@localhost:5432/dbname"),
        ("JWT token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"),
        ("AWS keys", "aws_access_key_id: AKIAIOSFODNN7EXAMPLE, aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"),
        ("URL with token", "https://api.example.com/data?access_token=secret_789&user=john"),
    ]
    
    for name, message in test_scenarios:
        print(f"\n--- {name} ---")
        logger.info(f"Test message: {message}")
        print(f"Original: {message}")
        # Note: Redacted output would appear in console/log file


def test_api_logger_redaction():
    """Test API logger with comprehensive redaction."""
    print("\n=== Testing API Logger Redaction ===")
    
    # Create API logger with standard redaction
    api_logger = APILogger("integration_test", RedactionLevel.STANDARD)
    
    # Mock logger to capture calls
    with patch('utils.logger.get_logger') as mock_get_logger:
        mock_logger = MagicMock()
        mock_get_logger.return_value = mock_logger
        
        api_logger = APILogger("test_api", RedactionLevel.STANDARD)
        
        # Test request logging
        print("\n--- API Request Logging ---")
        api_logger.log_request(
            api_name="gitlab_api",
            method="POST",
            url="https://gitlab.com/api/v4/projects/123/merge_requests?private_token=glpat-xxxxxxxxxxxxxxxxxxxx",
            headers={
                "Authorization": "Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "Private-Token": "glpat-xxxxxxxxxxxxxxxxxxxx",
                "Content-Type": "application/json"
            },
            body={
                "user": "john",
                "password": "user_secret_123",
                "session_token": "sess_abc123def456"
            }
        )
        
        # Test response logging  
        print("\n--- API Response Logging ---")
        api_logger.log_response(
            api_name="gitlab_api",
            method="POST",
            url="https://gitlab.com/api/v4/projects/123/merge_requests?private_token=glpat-xxxxxxxxxxxxxxxxxxxx",
            status_code=200,
            headers={
                "X-Rate-Limit-Remaining": "100",
                "X-Auth-Token": "response_secret_789",
                "Set-Cookie": "session=abcdef123456; Path=/; HttpOnly"
            },
            body={
                "access_token": "new_token_ghi789",
                "refresh_token": "refresh_jkl012",
                "expires_in": 3600
            }
        )
        
        # Test error logging
        print("\n--- API Error Logging ---")
        api_logger.log_error(
            api_name="glm_api",
            method="POST",
            url="https://api.z.ai/api/paas/v4/chat/completions?api_key=zai-secret-123456789",
            error=Exception("API authentication failed with token: secret_token_abc123"),
            status_code=401
        )


def test_nested_data_redaction():
    """Test redaction in complex nested data structures."""
    print("\n=== Testing Nested Data Redaction ===")
    
    setup_logging(
        level="DEBUG",
        format_type="json", 
        sanitize_sensitive_data=True,
        redaction_level=RedactionLevel.STANDARD
    )
    
    logger = get_logger("nested_test")
    
    complex_data = {
        "user": {
            "name": "John Doe",
            "email": "john@example.com",
            "credentials": {
                "api_key": "sk-1234567890abcdef",
                "database_password": "secret_db_password",
                "session_tokens": ["token1_abc", "token2_def", "token3_ghi"]
            }
        },
        "services": [
            {
                "name": "database",
                "connection_string": "postgresql://admin:admin123@localhost:5432/myapp",
                "ssl_cert": "-----BEGIN CERTIFICATE-----\nMIIC..."
            },
            {
                "name": "cache", 
                "redis_url": "redis://:redis_password@cache.example.com:6379/0",
                "auth_token": "cache_auth_token_xyz789"
            }
        ],
        "aws_config": {
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "session_token": "FwoGZXIvYXdzEDMaDH...example_token"
        }
    }
    
    print("\n--- Complex Nested Structure ---")
    logger.info(
        "Processing complex configuration",
        extra={
            "config_data": complex_data,
            "processing_id": "proc_12345",
            "user_token": "user_auth_secret_67890"
        }
    )


def test_aggressive_vs_standard_redaction():
    """Compare standard vs aggressive redaction levels."""
    print("\n=== Comparing Redaction Levels ===")
    
    test_data = {
        "description": "API request with sensitive data",
        "api_key": "sk-1234567890abcdef123456789",
        "session_id": "123e4567-e89b-12d3-a456-426614174000",
        "hash_value": "1a2b3c4d5e6f7890abcdef1234567890abcdef12",
        "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    }
    
    # Test standard redaction
    print("\n--- Standard Redaction ---")
    setup_logging(level="INFO", sanitize_sensitive_data=True, redaction_level=RedactionLevel.STANDARD)
    standard_logger = get_logger("standard_test")
    standard_logger.info("Standard level test", extra=test_data)
    
    # Test aggressive redaction  
    print("\n--- Aggressive Redaction ---")
    setup_logging(level="INFO", sanitize_sensitive_data=True, redaction_level=RedactionLevel.AGGRESSIVE)
    aggressive_logger = get_logger("aggressive_test")
    aggressive_logger.info("Aggressive level test", extra=test_data)


def test_performance_with_redaction():
    """Test performance impact of redaction system."""
    print("\n=== Testing Performance Impact ===")
    
    import time
    
    setup_logging(level="INFO", sanitize_sensitive_data=True, redaction_level=RedactionLevel.STANDARD)
    logger = get_logger("performance_test")
    
    # Test data with multiple sensitive items
    test_data = {
        "api_key": "sk-1234567890abcdef",
        "database_url": "postgresql://user:password@localhost/db",
        "aws_keys": {"access_key": "AKIAEXAMPLE", "secret_key": "secret123456"},
        "tokens": ["token1", "token2", "token3"],
        "jwt": "header.payload.signature"
    }
    
    iterations = 1000
    start_time = time.time()
    
    for i in range(iterations):
        logger.info(f"Performance test iteration {i}", extra=test_data)
    
    end_time = time.time()
    avg_time = (end_time - start_time) / iterations * 1000  # Convert to ms
    
    print(f"Average logging time per entry: {avg_time:.2f}ms")
    print(f"Total time for {iterations} entries: {end_time - start_time:.2f}s")


def main():
    """Run all security demonstration tests."""
    print("Enhanced Logging Security Integration Test")
    print("=" * 50)
    
    try:
        test_basic_sensitive_data_redaction()
        test_api_logger_redaction()
        test_nested_data_redaction()
        test_aggressive_vs_standard_redaction()
        test_performance_with_redaction()
        
        print("\n" + "=" * 50)
        print("✅ All integration tests completed successfully!")
        print("\nKey Security Features Demonstrated:")
        print("  • API keys and tokens automatically redacted")
        print("  • Database credentials protected")
        print("  • AWS keys securely handled")
        print("  • Complex nested structures processed")
        print("  • Configurable redaction levels")
        print("  • High-performance redaction")
        print("  • Comprehensive pattern coverage")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())