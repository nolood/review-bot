"""
Logging infrastructure for the GLM Code Review Bot.

Provides structured logging with configurable formats and levels.

This module offers comprehensive logging functionality with:
- JSON and text formatters with customizable output
- Specialized loggers for API and review operations
- Context-aware logging with GitLab integration
- Performance monitoring and metrics collection
- Secure logging with sensitive data redaction

Example:
    >>> from src.utils.logger import get_logger, setup_logging
    >>> setup_logging(level="DEBUG", format_type="json")
    >>> logger = get_logger(__name__)
    >>> logger.info("Application started", extra={"user_id": 123})
"""

import logging
import logging.config
import sys
import json
import os
from datetime import datetime
from typing import Dict, Any, Optional, Union, Literal, Set, List
from pathlib import Path
from enum import Enum

from ..config.settings import settings


# Constants for better maintainability
class LogLevel(Enum):
    """Supported logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class LogFormat(Enum):
    """Supported log formats."""
    JSON = "json"
    TEXT = "text"


# ANSI color codes for console output
class Colors:
    """ANSI color codes for console output."""
    CYAN = '\033[36m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    MAGENTA = '\033[35m'
    RESET = '\033[0m'
    
    # Mapping of log levels to colors
    LEVEL_COLORS = {
        LogLevel.DEBUG.value: CYAN,
        LogLevel.INFO.value: GREEN,
        LogLevel.WARNING.value: YELLOW,
        LogLevel.ERROR.value: RED,
        LogLevel.CRITICAL.value: MAGENTA,
    }


# Sensitive field patterns to redact in logs
SENSITIVE_FIELDS = {
    'authorization', 'token', 'password', 'secret', 'key',
    'api_key', 'private_key', 'access_token', 'refresh_token'
}

# Default timestamp format for text logs
DEFAULT_TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S'

# Standard log record fields to exclude when copying extra fields
STANDARD_LOG_FIELDS = {
    'name', 'msg', 'args', 'levelname', 'levelno', 'pathname',
    'filename', 'module', 'lineno', 'funcName', 'created',
    'msecs', 'relativeCreated', 'thread', 'threadName',
    'processName', 'process', 'getMessage', 'exc_info',
    'exc_text', 'stack_info'
}


# ============================================================================
# Formatter Classes
# ============================================================================

class JSONFormatter(logging.Formatter):
    """
    JSON formatter for structured logging.
    
    Converts log records to JSON format with consistent schema and 
    automatic context injection. Ideal for log aggregation systems.
    
    Example output:
        {
            "timestamp": "2023-12-01T10:30:45.123Z",
            "level": "INFO",
            "logger": "src.main",
            "message": "Processing completed",
            "module": "main",
            "function": "process_data",
            "line": 42,
            "project_id": 123,
            "mr_iid": 456
        }
    """
    
    def __init__(self, ensure_ascii: bool = False, sort_keys: bool = True):
        """
        Initialize JSON formatter.
        
        Args:
            ensure_ascii: Whether to ensure ASCII encoding in JSON output
            sort_keys: Whether to sort keys in JSON output
        """
        super().__init__()
        self.ensure_ascii = ensure_ascii
        self.sort_keys = sort_keys
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as JSON string.
        
        Args:
            record: The log record to format
            
        Returns:
            JSON-formatted log entry as string
            
        Raises:
            TypeError: If log entry contains non-serializable objects
        """
        try:
            log_entry = self._create_base_log_entry(record)
            self._add_context_info(log_entry)
            self._add_extra_fields(log_entry, record)
            self._add_exception_info(log_entry, record)
            
            return json.dumps(
                log_entry, 
                default=str, 
                ensure_ascii=self.ensure_ascii,
                sort_keys=self.sort_keys
            )
        except Exception as e:
            # Fallback to basic JSON format if formatting fails
            fallback_entry = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "level": "ERROR",
                "logger": "JSONFormatter",
                "message": f"Failed to format log record: {str(e)}",
                "original_record": str(record)
            }
            return json.dumps(fallback_entry, default=str)
    
    def _create_base_log_entry(self, record: logging.LogRecord) -> Dict[str, Any]:
        """Create the base log entry with standard fields."""
        return {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
    
    def _add_context_info(self, log_entry: Dict[str, Any]) -> None:
        """Add GitLab context information if available."""
        if settings.project_id:
            log_entry["project_id"] = settings.project_id
        if settings.mr_iid:
            log_entry["mr_iid"] = settings.mr_iid
    
    def _add_extra_fields(self, log_entry: Dict[str, Any], record: logging.LogRecord) -> None:
        """Add extra fields from the record while excluding standard fields."""
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_FIELDS:
                # Redact sensitive information in extra fields
                log_entry[key] = self._redact_sensitive_data(key, value)
    
    def _add_exception_info(self, log_entry: Dict[str, Any], record: logging.LogRecord) -> None:
        """Add exception information if present in the record."""
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
    
    def _redact_sensitive_data(self, key: str, value: Any) -> Any:
        """
        Redact sensitive data based on field names.
        
        Args:
            key: Field name to check
            value: Field value to potentially redact
            
        Returns:
            Original value or redacted placeholder
        """
        if key.lower() in SENSITIVE_FIELDS:
            return "***REDACTED***"
        return value


class TextFormatter(logging.Formatter):
    """
    Text formatter for human-readable logging with optional colors.
    
    Provides formatted text output with color coding for different log levels,
    context information, and proper exception formatting.
    
    Example output:
        [2023-12-01 10:30:45] INFO     src.main:42 - Processing completed (project=123, mr=456)
    """
    
    def __init__(self, use_colors: bool = True, timestamp_format: Optional[str] = None):
        """
        Initialize text formatter with colors for console output.
        
        Args:
            use_colors: Whether to use ANSI colors in output
            timestamp_format: Custom timestamp format string
        """
        super().__init__()
        self.use_colors = use_colors and self._supports_color()
        self.timestamp_format = timestamp_format or DEFAULT_TIMESTAMP_FORMAT
    
    def _supports_color(self) -> bool:
        """Check if the terminal supports color output."""
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()
    
    def format(self, record: logging.LogRecord) -> str:
        """
        Format log record as colored text.
        
        Args:
            record: The log record to format
            
        Returns:
            Formatted text log entry
        """
        timestamp = datetime.fromtimestamp(record.created).strftime(self.timestamp_format)
        
        # Build the base log message
        base_message = self._build_base_message(record, timestamp)
        
        # Add context information
        context_str = self._build_context_string()
        full_message = f"{base_message}{context_str}" if context_str else base_message
        
        # Add exception information if present
        if record.exc_info:
            full_message += f"\n{self.formatException(record.exc_info)}"
        
        # Apply colors if enabled
        if self.use_colors:
            color = Colors.LEVEL_COLORS.get(record.levelname, '')
            full_message = f"{color}{full_message}{Colors.RESET}"
        
        return full_message
    
    def _build_base_message(self, record: logging.LogRecord, timestamp: str) -> str:
        """Build the base log message with timestamp, level, and message."""
        return (
            f"[{timestamp}] {record.levelname:8} "
            f"{record.name}:{record.lineno} - {record.getMessage()}"
        )
    
    def _build_context_string(self) -> str:
        """Build context information string if available."""
        context_parts = []
        if settings.project_id:
            context_parts.append(f"project={settings.project_id}")
        if settings.mr_iid:
            context_parts.append(f"mr={settings.mr_iid}")
        
        return f" ({', '.join(context_parts)})" if context_parts else ""


# ============================================================================
# Filter Classes
# ============================================================================

class ContextFilter(logging.Filter):
    """
    Filter to add context information to log records.
    
    Automatically injects GitLab context (project_id, mr_iid) into all
    log records that pass through this filter.
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Add context information to the log record.
        
        Args:
            record: The log record to enhance
            
        Returns:
            Always returns True to allow the record through
        """
        record.project_id = settings.project_id
        record.mr_iid = settings.mr_iid
        return True


class SensitiveDataFilter(logging.Filter):
    """
    Filter to sanitize sensitive data in log records.
    
    Automatically redacts sensitive information from log messages
    and extra fields to prevent accidental exposure of credentials.
    """
    
    def __init__(self, sensitive_fields: Optional[Set[str]] = None):
        """
        Initialize sensitive data filter.
        
        Args:
            sensitive_fields: Custom set of field names to redact
        """
        super().__init__()
        self.sensitive_fields = sensitive_fields or SENSITIVE_FIELDS
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Sanitize sensitive data in the log record.
        
        Args:
            record: The log record to sanitize
            
        Returns:
            Always returns True to allow the record through
        """
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            record.msg = self._sanitize_message(record.msg)
        
        # Sanitize extra fields
        for key in list(record.__dict__.keys()):
            if key.lower() in self.sensitive_fields:
                setattr(record, key, "***REDACTED***")
        
        return True
    
    def _sanitize_message(self, message: str) -> str:
        """Sanitize message content for sensitive information."""
        import re
        
        # Basic pattern to detect potential sensitive data
        # This is a simple implementation - could be enhanced with more sophisticated patterns
        patterns = [
            (r'(token["\s]*[:=]["\s]*)([^"\s]+)', r'\1***REDACTED***'),
            (r'(key["\s]*[:=]["\s]*)([^"\s]+)', r'\1***REDACTED***'),
            (r'(password["\s]*[:=]["\s]*)([^"\s]+)', r'\1***REDACTED***'),
        ]
        
        for pattern, replacement in patterns:
            message = re.sub(pattern, replacement, message, flags=re.IGNORECASE)
        
        return message


# ============================================================================
# Logger Setup and Configuration
# ============================================================================

def validate_log_level(level: str) -> str:
    """
    Validate and normalize log level string.
    
    Args:
        level: Log level string to validate
        
    Returns:
        Validated log level string
        
    Raises:
        ValueError: If the log level is not supported
    """
    if not level:
        raise ValueError("Log level cannot be empty")
    
    level_upper = level.upper()
    valid_levels = {log_level.value for log_level in LogLevel}
    
    if level_upper not in valid_levels:
        raise ValueError(f"Invalid log level: {level}. Valid levels: {', '.join(valid_levels)}")
    
    return level_upper


def validate_log_format(format_type: str) -> str:
    """
    Validate and normalize log format string.
    
    Args:
        format_type: Log format string to validate
        
    Returns:
        Validated log format string
        
    Raises:
        ValueError: If the log format is not supported
    """
    if not format_type:
        raise ValueError("Log format cannot be empty")
    
    format_lower = format_type.lower()
    valid_formats = {log_format.value for log_format in LogFormat}
    
    if format_lower not in valid_formats:
        raise ValueError(f"Invalid log format: {format_type}. Valid formats: {', '.join(valid_formats)}")
    
    return format_lower


def setup_logging(
    level: Optional[Union[str, LogLevel]] = None,
    format_type: Optional[Union[str, LogFormat]] = None,
    log_file: Optional[str] = None,
    use_colors: Optional[bool] = None,
    sanitize_sensitive_data: bool = True,
    custom_format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up comprehensive logging configuration.
    
    Configures the root logger with appropriate handlers, formatters,
    and filters. Supports both JSON and text output formats with optional
    file logging and sensitive data sanitization.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format ('json' or 'text')
        log_file: Optional log file path
        use_colors: Whether to use colors in text output (auto-detected if None)
        sanitize_sensitive_data: Whether to filter sensitive information
        custom_format_string: Custom timestamp format for text output
        
    Returns:
        Configured logger instance
        
    Raises:
        ValueError: If validation fails for level or format
        OSError: If log file cannot be created
        PermissionError: If insufficient permissions for log file
        
    Example:
        >>> logger = setup_logging(
        ...     level="DEBUG",
        ...     format_type="text",
        ...     log_file="/var/log/app.log",
        ...     sanitize_sensitive_data=True
        ... )
    """
    # Use settings defaults if not provided
    level_str = str(level) if level else settings.log_level
    format_str = str(format_type) if format_type else settings.log_format
    log_file_path = log_file or settings.log_file
    
    # Validate inputs
    try:
        validated_level = validate_log_level(level_str)
        validated_format = validate_log_format(format_str)
    except ValueError as e:
        # Fallback to safe defaults if validation fails
        validated_level = LogLevel.INFO.value
        validated_format = LogFormat.TEXT.value
        print(f"Warning: {e}. Using fallback settings.", file=sys.stderr)
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, validated_level, logging.INFO)
    
    # Create and configure root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicate logs
    logger.handlers.clear()
    
    # Create filters
    filters: List[logging.Filter] = [ContextFilter()]
    if sanitize_sensitive_data:
        filters.append(SensitiveDataFilter())
    
    # Create formatters
    if validated_format == LogFormat.JSON.value:
        console_formatter = JSONFormatter()
        file_formatter = JSONFormatter(ensure_ascii=False, sort_keys=True)
    else:
        use_colors_enabled = use_colors if use_colors is not None else True
        console_formatter = TextFormatter(
            use_colors=use_colors_enabled,
            timestamp_format=custom_format_string
        )
        file_formatter = JSONFormatter()  # Always use JSON for files
    
    # Setup console handler
    try:
        console_handler = _create_console_handler(
            numeric_level, console_formatter, filters
        )
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Warning: Failed to create console handler: {e}", file=sys.stderr)
    
    # Setup file handler if specified
    if log_file_path:
        try:
            file_handler = _create_file_handler(
                log_file_path, numeric_level, file_formatter, filters
            )
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            print(f"Warning: Failed to create file handler: {e}", file=sys.stderr)
    
    return logger


def _create_console_handler(
    level: int, 
    formatter: logging.Formatter, 
    filters: List[logging.Filter]
) -> logging.StreamHandler:
    """Create and configure a console log handler."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(level)
    handler.setFormatter(formatter)
    
    for filter_obj in filters:
        handler.addFilter(filter_obj)
    
    return handler


def _create_file_handler(
    log_file: str,
    level: int,
    formatter: logging.Formatter,
    filters: List[logging.Filter]
) -> logging.FileHandler:
    """Create and configure a file log handler."""
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create file handler
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setLevel(level)
    handler.setFormatter(formatter)
    
    for filter_obj in filters:
        handler.addFilter(filter_obj)
    
    return handler


def _create_file_handler(
    log_file: str,
    level: int,
    formatter: logging.Formatter,
    filters: list
) -> logging.FileHandler:
    """Create and configure a file log handler."""
    # Ensure log directory exists
    log_path = Path(log_file)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create file handler
    handler = logging.FileHandler(log_file, encoding='utf-8')
    handler.setLevel(level)
    handler.setFormatter(formatter)
    
    for filter_obj in filters:
        handler.addFilter(filter_obj)
    
    return handler


def setup_logging(
    level: Optional[Union[str, LogLevel]] = None,
    format_type: Optional[Union[str, LogFormat]] = None,
    log_file: Optional[str] = None,
    use_colors: Optional[bool] = None,
    sanitize_sensitive_data: bool = True,
    custom_format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up comprehensive logging configuration.
    
    Configures the root logger with appropriate handlers, formatters,
    and filters. Supports both JSON and text output formats with optional
    file logging and sensitive data sanitization.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format ('json' or 'text')
        log_file: Optional log file path
        use_colors: Whether to use colors in text output (auto-detected if None)
        sanitize_sensitive_data: Whether to filter sensitive information
        custom_format_string: Custom timestamp format for text output
        
    Returns:
        Configured logger instance
        
    Raises:
        ValueError: If validation fails for level or format
        OSError: If log file cannot be created
        PermissionError: If insufficient permissions for log file
        
    Example:
        >>> logger = setup_logging(
        ...     level="DEBUG",
        ...     format_type="text",
        ...     log_file="/var/log/app.log",
        ...     sanitize_sensitive_data=True
        ... )
    """
    # Use settings defaults if not provided
    level_str = str(level) if level else settings.log_level
    format_str = str(format_type) if format_type else settings.log_format
    log_file_path = log_file or settings.log_file
    
    # Validate inputs
    try:
        validated_level = validate_log_level(level_str)
        validated_format = validate_log_format(format_str)
    except ValueError as e:
        # Fallback to safe defaults if validation fails
        validated_level = LogLevel.INFO.value
        validated_format = LogFormat.TEXT.value
        print(f"Warning: {e}. Using fallback settings.", file=sys.stderr)
    
    # Convert level string to logging constant
    numeric_level = getattr(logging, validated_level, logging.INFO)
    
    # Create and configure root logger
    logger = logging.getLogger()
    logger.setLevel(numeric_level)
    
    # Clear existing handlers to avoid duplicate logs
    logger.handlers.clear()
    
    # Create filters
    filters = [ContextFilter()]
    if sanitize_sensitive_data:
        filters.append(SensitiveDataFilter())
    
    # Create formatters
    if validated_format == LogFormat.JSON.value:
        console_formatter = JSONFormatter()
        file_formatter = JSONFormatter(ensure_ascii=False, sort_keys=True)
    else:
        use_colors_enabled = use_colors if use_colors is not None else True
        console_formatter = TextFormatter(
            use_colors=use_colors_enabled,
            timestamp_format=custom_format_string
        )
        file_formatter = JSONFormatter()  # Always use JSON for files
    
    # Setup console handler
    try:
        console_handler = _create_console_handler(
            numeric_level, console_formatter, filters
        )
        logger.addHandler(console_handler)
    except Exception as e:
        print(f"Warning: Failed to create console handler: {e}", file=sys.stderr)
    
    # Setup file handler if specified
    if log_file_path:
        try:
            file_handler = _create_file_handler(
                log_file_path, numeric_level, file_formatter, filters
            )
            logger.addHandler(file_handler)
        except (OSError, PermissionError) as e:
            print(f"Warning: Failed to create file handler: {e}", file=sys.stderr)
    
    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the specified name.
    
    Args:
        name: Logger name (typically __name__)
        
    Returns:
        Logger instance
    """
    return logging.getLogger(name)


class APILogger:
    """Specialized logger for API interactions."""
    
    def __init__(self, logger_name: str = "api"):
        """Initialize API logger."""
        self.logger = get_logger(logger_name)
    
    def log_request(
        self,
        api_name: str,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None
    ):
        """Log an API request."""
        # Sanitize headers to remove sensitive information
        sanitized_headers = headers.copy()
        if 'authorization' in sanitized_headers:
            sanitized_headers['authorization'] = '***REDACTED***'
        
        self.logger.info(
            f"API Request: {method} {url}",
            extra={
                "api_name": api_name,
                "method": method,
                "url": url,
                "headers": sanitized_headers,
                "has_body": body is not None
            }
        )
        
        if body and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"API Request Body: {method} {url}",
                extra={
                    "api_name": api_name,
                    "method": method,
                    "url": url,
                    "body": body
                }
            )
    
    def log_response(
        self,
        api_name: str,
        method: str,
        url: str,
        status_code: int,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None,
        response_time_ms: Optional[float] = None
    ):
        """Log an API response."""
        self.logger.info(
            f"API Response: {method} {url} - {status_code}",
            extra={
                "api_name": api_name,
                "method": method,
                "url": url,
                "status_code": status_code,
                "headers": headers,
                "response_time_ms": response_time_ms
            }
        )
        
        if body and self.logger.isEnabledFor(logging.DEBUG):
            self.logger.debug(
                f"API Response Body: {method} {url}",
                extra={
                    "api_name": api_name,
                    "method": method,
                    "url": url,
                    "body": body
                }
            )
    
    def log_error(
        self,
        api_name: str,
        method: str,
        url: str,
        error: Exception,
        status_code: Optional[int] = None,
        response_body: Optional[Dict[str, Any]] = None
    ):
        """Log an API error."""
        self.logger.error(
            f"API Error: {method} {url} - {error}",
            extra={
                "api_name": api_name,
                "method": method,
                "url": url,
                "status_code": status_code,
                "error_type": type(error).__name__,
                "error_message": str(error),
                "has_response_body": response_body is not None
            },
            exc_info=True
        )


class ReviewLogger:
    """Specialized logger for code review operations."""
    
    def __init__(self, logger_name: str = "review"):
        """Initialize review logger."""
        self.logger = get_logger(logger_name)
    
    def log_diff_processing(
        self,
        file_count: int,
        total_lines: int,
        estimated_tokens: int,
        processing_time_ms: float
    ):
        """Log diff processing statistics."""
        self.logger.info(
            "Diff processing completed",
            extra={
                "file_count": file_count,
                "total_lines": total_lines,
                "estimated_tokens": estimated_tokens,
                "processing_time_ms": processing_time_ms
            }
        )
    
    def log_review_generation(
        self,
        chunks_processed: int,
        total_tokens_used: int,
        comments_generated: int,
        processing_time_ms: float
    ):
        """Log review generation statistics."""
        self.logger.info(
            "Review generation completed",
            extra={
                "chunks_processed": chunks_processed,
                "total_tokens_used": total_tokens_used,
                "comments_generated": comments_generated,
                "processing_time_ms": processing_time_ms
            }
        )
    
    def log_comment_publication(
        self,
        total_comments: int,
        inline_comments: int,
        summary_comments: int,
        publication_time_ms: float
    ):
        """Log comment publication statistics."""
        self.logger.info(
            "Comment publication completed",
            extra={
                "total_comments": total_comments,
                "inline_comments": inline_comments,
                "summary_comments": summary_comments,
                "publication_time_ms": publication_time_ms
            }
        )


# Initialize logging with default settings
setup_logging()

# Create specialized loggers
api_logger = APILogger()
review_logger = ReviewLogger()

# Export the main logger function
__all__ = [
    "setup_logging",
    "get_logger",
    "APILogger",
    "ReviewLogger",
    "api_logger",
    "review_logger"
]