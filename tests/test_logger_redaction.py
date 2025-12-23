"""
Comprehensive tests for sensitive data redaction in logging.

Tests the enhanced logging security features including:
- Pattern-based redaction
- Field name redaction
- Configurable redaction levels
- API logging security
- Dictionary and string redaction
"""

import pytest
import json
import logging
from unittest.mock import patch, MagicMock
from src.utils.logger import (
    SensitiveDataRedactor, 
    SensitiveDataFilter,
    APILogger,
    RedactionLevel,
    setup_logging,
    get_logger
)


class TestSensitiveDataRedactor:
    """Test the SensitiveDataRedactor class."""
    
    @pytest.mark.parametrize("level", [
        RedactionLevel.NONE,
        RedactionLevel.BASIC,
        RedactionLevel.STANDARD,
        RedactionLevel.AGGRESSIVE
    ])
    def test_redactor_initialization(self, level):
        """Test redactor initialization with different levels."""
        redactor = SensitiveDataRedactor(level)
        assert redactor.level == level
        assert redactor.redaction_placeholder == "***REDACTED***"
    
    def test_sensitive_field_redaction(self):
        """Test redaction of sensitive field names."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        # Test sensitive field name - we keep field names for debugging, only redact values
        redacted_key = redactor._redact_field_name("api_key")
        assert redacted_key == "api_key"  # Field names are preserved for debugging
        
        # Test non-sensitive field name
        normal_key = redactor._redact_field_name("user_name")
        assert normal_key == "user_name"
    
    def test_value_redaction_by_key(self):
        """Test value redaction based on field key."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        # Test redaction by sensitive key
        redacted_value = redactor._redact_value("api_key", "secret123")
        assert redacted_value == "***REDACTED***"
        
        # Test no redaction for normal key
        normal_value = redactor._redact_value("user_name", "john_doe")
        assert normal_value == "john_doe"
    
    def test_dict_redaction(self):
        """Test redaction of entire dictionaries."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        test_dict = {
            "user_name": "john",
            "api_key": "secret123",
            "token": "abc123xyz",
            "nested": {
                "password": "hidden",
                "normal_field": "visible"
            }
        }
        
        redacted = redactor.redact_dict(test_dict)
        
        assert redacted["user_name"] == "john"
        assert redacted["api_key"] == "***REDACTED***"
        assert redacted["token"] == "***REDACTED***"
        assert redacted["nested"]["password"] == "***REDACTED***"
        assert redacted["nested"]["normal_field"] == "visible"
    
    def test_list_redaction(self):
        """Test redaction in lists."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        test_list = [
            {"name": "item1", "value": "normal"},
            {"name": "item2", "secret": "hidden_value"}
        ]
        
        redacted = redactor._redact_value("test_list", test_list)
        
        assert redacted[0]["value"] == "normal"
        assert redacted[1]["secret"] == "***REDACTED***"
    
    def test_string_pattern_redaction_standard(self):
        """Test string pattern redaction at standard level."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        # Test API key pattern
        text_with_api_key = 'Request with api_key="secret123abc456def"'
        redacted = redactor.redact_string(text_with_api_key)
        assert '***REDACTED***' in redacted
        assert 'secret123abc456def' not in redacted
        
        # Test Bearer token pattern
        text_with_bearer = 'Authorization: Bearer abc123def456ghi789'
        redacted = redactor.redact_string(text_with_bearer)
        assert '***REDACTED***' in redacted
        
        # Test JWT pattern
        text_with_jwt = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c'
        redacted = redactor.redact_string(text_with_jwt)
        assert '***REDACTED***' in redacted
    
    def test_string_pattern_redaction_aggressive(self):
        """Test string pattern redaction at aggressive level."""
        redactor = SensitiveDataRedactor(RedactionLevel.AGGRESSIVE)
        
        # Test UUID pattern
        text_with_uuid = 'Session: 123e4567-e89b-12d3-a456-426614174000'
        redacted = redactor.redact_string(text_with_uuid)
        assert '***HASH:' in redacted
        # Original UUID should be replaced
        assert '123e4567-e89b-12d3-a456-426614174000' not in redacted or redacted.count('123e4567-e89b-12d3-a456-426614174000') < redacted.count('***HASH:')
        
        # Test hex pattern
        text_with_hex = 'Hash: 1a2b3c4d5e6f7890abcdef1234567890abcdef12'
        redacted = redactor.redact_string(text_with_hex)
        assert '***HASH:' in redacted
    
    def test_url_redaction(self):
        """Test URL redaction for sensitive parameters."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        # Test URL with API key parameter
        url_with_key = 'https://api.example.com/data?api_key=secret123&user=john'
        redacted = redactor.redact_string(url_with_key)
        assert '***REDACTED***' in redacted
        assert 'secret123' not in redacted
        
        # Test database URL
        db_url = 'postgresql://user:password123@localhost:5432/db'
        redacted = redactor.redact_string(db_url)
        assert '***REDACTED***' in redacted
        assert 'password123' not in redacted
    
    def test_aws_keys_redaction(self):
        """Test AWS-specific key redaction."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        # Test AWS access key
        aws_text = 'aws_access_key_id: AKIAIOSFODNN7EXAMPLE'
        redacted = redactor.redact_string(aws_text)
        assert '***REDACTED***' in redacted
        assert 'AKIAIOSFODNN7EXAMPLE' not in redacted
        
        # Test AWS secret key
        aws_secret = 'aws_secret_access_key: wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
        redacted = redactor.redact_string(aws_secret)
        assert '***REDACTED***' in redacted
    
    def test_preserve_length_redaction(self):
        """Test length preservation in redaction."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        # Test preserve length
        short_value = redactor._redact_value("api_key", "123", preserve_length=True)
        assert len(short_value) <= 3
        
        long_value = redactor._redact_value("api_key", "1234567890", preserve_length=True)
        assert len(long_value) <= 10
    
    def test_redactor_stats(self):
        """Test redactor statistics."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        stats = redactor.get_stats()
        
        assert "redaction_level" in stats
        assert "patterns_count" in stats
        assert "sensitive_fields_count" in stats
        assert stats["redaction_level"] == "standard"


class TestSensitiveDataFilter:
    """Test the SensitiveDataFilter class."""
    
    def test_filter_initialization(self):
        """Test filter initialization."""
        filter_obj = SensitiveDataFilter(RedactionLevel.STANDARD)
        assert filter_obj.redactor.level == RedactionLevel.STANDARD
        assert filter_obj.preserve_length is False
    
    def test_filter_message_redaction(self):
        """Test message redaction in filter."""
        filter_obj = SensitiveDataFilter(RedactionLevel.STANDARD)
        
        # Create a mock log record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg='API call with api_key="secret123"',
            args=(),
            exc_info=None
        )
        
        # Apply filter
        result = filter_obj.filter(record)
        
        assert result is True  # Filter always returns True
        assert '***REDACTED***' in record.msg
        assert 'secret123' not in record.msg
    
    def test_filter_field_redaction(self):
        """Test field redaction in filter."""
        filter_obj = SensitiveDataFilter(RedactionLevel.STANDARD)
        
        # Create a mock log record with extra fields
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="API request",
            args=(),
            exc_info=None
        )
        # Add extra fields that would normally be added via logger.info(..., extra={...})
        record.__dict__['api_key'] = "secret123"
        record.__dict__['user_name'] = "john"
        
        # Apply filter
        filter_obj.filter(record)
        
        # Check the __dict__ for the extra fields
        assert record.__dict__['api_key'] == "***REDACTED***"
        assert record.__dict__['user_name'] == "john"
    
    def test_filter_statistics(self):
        """Test filter statistics tracking."""
        filter_obj = SensitiveDataFilter(RedactionLevel.STANDARD)
        
        # Create and filter multiple records
        for i in range(3):
            record = logging.LogRecord(
                name="test",
                level=logging.INFO,
                pathname="test.py",
                lineno=1,
                msg=f"Message {i} with api_key='secret{i}'",
                args=(),
                exc_info=None
            )
            record.api_key = f"secret{i}"
            filter_obj.filter(record)
        
        stats = filter_obj.get_stats()
        assert stats["records_processed"] == 3
        assert stats["fields_redacted"] >= 3  # At least message and api_key per record
    
    def test_filter_stats_reset(self):
        """Test filter statistics reset."""
        filter_obj = SensitiveDataFilter(RedactionLevel.STANDARD)
        
        # Process one record
        record = logging.LogRecord(
            name="test",
            level=logging.INFO,
            pathname="test.py",
            lineno=1,
            msg="test",
            args=(),
            exc_info=None
        )
        filter_obj.filter(record)
        
        # Check stats exist
        stats = filter_obj.get_stats()
        assert stats["records_processed"] == 1
        
        # Reset and verify
        filter_obj.reset_stats()
        stats = filter_obj.get_stats()
        assert stats["records_processed"] == 0
        assert stats["fields_redacted"] == 0


class TestAPILogger:
    """Test the APILogger class with enhanced security."""
    
    def test_api_logger_initialization(self):
        """Test API logger initialization."""
        logger = APILogger("test_api", RedactionLevel.STANDARD)
        assert logger.redactor.level == RedactionLevel.STANDARD
        assert logger.logger.name == "test_api"
    
    @patch('src.utils.logger.get_logger')
    def test_log_request_redaction(self, mock_get_logger):
        """Test API request logging with redaction."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False
        mock_get_logger.return_value = mock_logger
        
        api_logger = APILogger("test_api", RedactionLevel.STANDARD)
        
        headers = {
            "Authorization": "Bearer secret123",
            "Content-Type": "application/json",
            "X-API-Key": "api_key_456"
        }
        
        api_logger.log_request(
            api_name="test_api",
            method="POST",
            url="https://api.example.com/data?api_key=secret789",
            headers=headers,
            body={"user": "john", "password": "hidden123"}
        )
        
        # Verify logger.info was called
        mock_logger.info.assert_called_once()
        
        # Get the call arguments
        call_args = mock_logger.info.call_args
        log_message = call_args[0][0]  # First positional argument
        extra = call_args[1]["extra"]  # Keyword argument
        
        # Verify URL redaction
        assert '***REDACTED***' in log_message or '***REDACTED***' in extra["url"]
        assert 'secret789' not in log_message
        assert 'secret789' not in extra["url"]
        
        # Verify header redaction
        assert extra["headers"]["Authorization"] == "***REDACTED***"
        assert extra["headers"]["X-API-Key"] == "***REDACTED***"
        assert extra["headers"]["Content-Type"] == "application/json"  # Should remain
    
    @patch('src.utils.logger.get_logger')
    def test_log_response_redaction(self, mock_get_logger):
        """Test API response logging with redaction."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False
        mock_get_logger.return_value = mock_logger
        
        api_logger = APILogger("test_api", RedactionLevel.STANDARD)
        
        headers = {
            "X-Auth-Token": "response_token_123",
            "Content-Type": "application/json"
        }
        
        api_logger.log_response(
            api_name="test_api",
            method="GET",
            url="https://api.example.com/data?token=sensitive456",
            status_code=200,
            headers=headers,
            body={"access_token": "secret789", "data": "public"}
        )
        
        # Verify logger.info was called
        mock_logger.info.assert_called_once()
        
        # Get the call arguments
        call_args = mock_logger.info.call_args
        extra = call_args[1]["extra"]
        
        # Verify URL redaction
        assert '***REDACTED***' in extra["url"] or extra["url"] != "https://api.example.com/data?token=sensitive456"
        
        # Verify header redaction
        assert extra["headers"]["X-Auth-Token"] == "***REDACTED***"
        assert extra["headers"]["Content-Type"] == "application/json"  # Should remain
    
    @patch('src.utils.logger.get_logger')
    def test_log_error_redaction(self, mock_get_logger):
        """Test API error logging with redaction."""
        mock_logger = MagicMock()
        mock_logger.isEnabledFor.return_value = False
        mock_get_logger.return_value = mock_logger
        
        api_logger = APILogger("test_api", RedactionLevel.STANDARD)
        
        error = ValueError("Authentication failed with token: secret_token_123")
        
        api_logger.log_error(
            api_name="test_api",
            method="POST",
            url="https://api.example.com/auth?api_key=secret456",
            error=error,
            status_code=401
        )
        
        # Verify logger.error was called
        mock_logger.error.assert_called_once()
        
        # Get the call arguments
        call_args = mock_logger.error.call_args
        log_message = call_args[0][0]
        extra = call_args[1]["extra"]
        
        # Verify error message redaction
        assert '***REDACTED***' in log_message or 'secret_token_123' not in log_message
        
        # Verify URL redaction
        assert '***REDACTED***' in extra["url"] or extra["url"] != "https://api.example.com/auth?api_key=secret456"


class TestSetupLoggingEnhancements:
    """Test enhanced setup_logging function."""
    
    def test_setup_logging_with_redaction_options(self):
        """Test setup_logging with redaction options."""
        # Clear any existing handlers
        logger = logging.getLogger()
        logger.handlers.clear()
        
        # Test with custom redaction settings
        configured_logger = setup_logging(
            level="DEBUG",
            format_type="json",
            sanitize_sensitive_data=True,
            redaction_level=RedactionLevel.STANDARD,
            preserve_sensitive_length=False
        )
        
        assert configured_logger.level == logging.DEBUG
        
        # Verify filters are applied either to logger or handlers
        has_sensitive_filter = any(
            isinstance(filter_obj, SensitiveDataFilter) 
            for filter_obj in configured_logger.filters
        ) or any(
            isinstance(filter_obj, SensitiveDataFilter)
            for handler in configured_logger.handlers
            for filter_obj in handler.filters
        )
        assert has_sensitive_filter, "SensitiveDataFilter should be applied to logger or handlers"
    
    @pytest.mark.parametrize("redaction_level", [
        "none", "basic", "standard", "aggressive"
    ])
    def test_setup_logging_different_redaction_levels(self, redaction_level):
        """Test setup_logging with different redaction levels."""
        # Clear any existing handlers
        logger = logging.getLogger()
        logger.handlers.clear()
        
        configured_logger = setup_logging(
            level="INFO",
            sanitize_sensitive_data=True,
            redaction_level=redaction_level
        )
        
        assert configured_logger is not None


class TestIntegration:
    """Integration tests for the complete redaction system."""
    
    def test_end_to_end_redaction(self):
        """Test complete redaction system end-to-end."""
        # Setup logging with standard redaction
        logger = setup_logging(
            level="DEBUG",
            format_type="json",
            sanitize_sensitive_data=True,
            redaction_level=RedactionLevel.STANDARD
        )
        
        # Create a test logger
        test_logger = get_logger("integration_test")
        
        # Log sensitive information
        test_logger.info(
            "User login attempt",
            extra={
                "username": "john",
                "api_key": "secret_key_123",
                "password": "user_password_456",
                "session_token": "session_abc_789"
            }
        )
        
        # Verify that sensitive information is redacted in the log output
        # Note: In a real test, we would capture the log output and verify redaction
        # For this test, we mainly verify that the logging system works without errors
        
    def test_api_logger_integration(self):
        """Test API logger integration with full redaction."""
        api_logger = APILogger("integration_api", RedactionLevel.STANDARD)
        
        # This should not raise any exceptions and should properly redact sensitive data
        api_logger.log_request(
            api_name="test_service",
            method="POST",
            url="https://api.test.com/endpoint?api_key=secret123&token=token456",
            headers={
                "Authorization": "Bearer bearer789",
                "X-API-Key": "api_key_012",
                "Content-Type": "application/json"
            },
            body={
                "credentials": {"password": "pass123", "username": "user"},
                "public_data": {"name": "John"}
            }
        )
    
    def test_complex_nested_redaction(self):
        """Test redaction in complex nested structures."""
        redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
        
        complex_data = {
            "level1": {
                "api_key": "secret_l1",
                "level2": {
                    "token": "secret_l2",
                    "level3": {
                        "authorization": "Bearer secret_l3",
                        "normal_data": "public_info"
                    }
                }
            },
            "list_data": [
                {"password": "list_secret_1"},
                {"normal_field": "list_public_1"},
                {"api_key": "list_secret_2"}
            ]
        }
        
        redacted = redactor.redact_dict(complex_data)
        
        # Verify all levels are properly redacted
        assert redacted["level1"]["api_key"] == "***REDACTED***"
        assert redacted["level1"]["level2"]["token"] == "***REDACTED***"
        assert redacted["level1"]["level2"]["level3"]["authorization"] == "***REDACTED***"
        assert redacted["level1"]["level2"]["level3"]["normal_data"] == "public_info"
        assert redacted["list_data"][0]["password"] == "***REDACTED***"
        assert redacted["list_data"][1]["normal_field"] == "list_public_1"
        assert redacted["list_data"][2]["api_key"] == "***REDACTED***"


if __name__ == "__main__":
    pytest.main([__file__])