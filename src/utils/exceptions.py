"""
Custom exception classes for the GLM Code Review Bot.

Provides specific exception types for different error scenarios
with appropriate error codes and messages.
"""

from typing import Optional, Dict, Any


class ReviewBotError(Exception):
    """
    Base exception for the GLM Code Review Bot.
    
    All custom exceptions should inherit from this class.
    """
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the exception.
        
        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary representation."""
        return {
            "error_type": self.__class__.__name__,
            "error_code": self.error_code,
            "message": self.message,
            "details": self.details
        }


class ConfigurationError(ReviewBotError):
    """
    Raised when there's a configuration error.
    
    This includes missing environment variables,
    invalid configuration values, etc.
    """
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        config_value: Optional[str] = None
    ):
        """Initialize configuration error."""
        details = {}
        if config_key:
            details["config_key"] = config_key
        if config_value:
            details["config_value"] = config_value
        
        super().__init__(
            message=message,
            error_code="CONFIG_ERROR",
            details=details
        )


class GLMAPIError(ReviewBotError):
    """
    Raised when there's an error with the GLM API.
    
    This includes network errors, API errors, rate limiting,
    invalid responses, etc.
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
        request_id: Optional[str] = None
    ):
        """Initialize GLM API error."""
        details = {}
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body
        if request_id:
            details["request_id"] = request_id
        
        super().__init__(
            message=message,
            error_code="GLM_API_ERROR",
            details=details
        )


class GitLabAPIError(ReviewBotError):
    """
    Raised when there's an error with the GitLab API.
    
    This includes authentication errors, permission issues,
    resource not found, etc.
    """
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None,
        endpoint: Optional[str] = None
    ):
        """Initialize GitLab API error."""
        details = {}
        if status_code:
            details["status_code"] = status_code
        if response_body:
            details["response_body"] = response_body
        if endpoint:
            details["endpoint"] = endpoint
        
        super().__init__(
            message=message,
            error_code="GITLAB_API_ERROR",
            details=details
        )


class DiffParsingError(ReviewBotError):
    """
    Raised when there's an error parsing a git diff.
    
    This includes malformed diffs, encoding issues,
    unsupported diff formats, etc.
    """
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        diff_line: Optional[int] = None,
        diff_content: Optional[str] = None
    ):
        """Initialize diff parsing error."""
        details = {}
        if file_path:
            details["file_path"] = file_path
        if diff_line:
            details["diff_line"] = diff_line
        if diff_content:
            details["diff_content"] = diff_content
        
        super().__init__(
            message=message,
            error_code="DIFF_PARSING_ERROR",
            details=details
        )


class CommentPublishError(ReviewBotError):
    """
    Raised when there's an error publishing comments.
    
    This includes failed API calls, rate limiting,
    permission issues, etc.
    """
    
    def __init__(
        self,
        message: str,
        comment_count: Optional[int] = None,
        file_path: Optional[str] = None,
        line_number: Optional[int] = None
    ):
        """Initialize comment publish error."""
        details = {}
        if comment_count:
            details["comment_count"] = comment_count
        if file_path:
            details["file_path"] = file_path
        if line_number:
            details["line_number"] = line_number
        
        super().__init__(
            message=message,
            error_code="COMMENT_PUBLISH_ERROR",
            details=details
        )


class TokenLimitError(ReviewBotError):
    """
    Raised when token limits are exceeded.
    
    This includes diff too large, response too large,
    token limit exceeded, etc.
    """
    
    def __init__(
        self,
        message: str,
        token_count: Optional[int] = None,
        token_limit: Optional[int] = None,
        resource_type: Optional[str] = None
    ):
        """Initialize token limit error."""
        details = {}
        if token_count:
            details["token_count"] = token_count
        if token_limit:
            details["token_limit"] = token_limit
        if resource_type:
            details["resource_type"] = resource_type
        
        super().__init__(
            message=message,
            error_code="TOKEN_LIMIT_ERROR",
            details=details
        )


class TimeoutError(ReviewBotError):
    """
    Raised when operations timeout.
    
    This includes API requests, processing operations,
    etc. that exceed their time limits.
    """
    
    def __init__(
        self,
        message: str,
        timeout_seconds: Optional[int] = None,
        operation: Optional[str] = None
    ):
        """Initialize timeout error."""
        details = {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        if operation:
            details["operation"] = operation
        
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            details=details
        )


class RetryExhaustedError(ReviewBotError):
    """
    Raised when all retry attempts are exhausted.
    
    This indicates that an operation failed repeatedly
    despite retry attempts.
    """
    
    def __init__(
        self,
        message: str,
        attempts: Optional[int] = None,
        last_error: Optional[Exception] = None
    ):
        """Initialize retry exhausted error."""
        details = {}
        if attempts:
            details["attempts"] = attempts
        if last_error:
            details["last_error_type"] = type(last_error).__name__
            details["last_error_message"] = str(last_error)
        
        super().__init__(
            message=message,
            error_code="RETRY_EXHAUSTED_ERROR",
            details=details
        )