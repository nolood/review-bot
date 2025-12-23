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
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, Union, Set, List, Pattern
from pathlib import Path
from enum import Enum

try:
    from ..config.settings import settings
except ImportError:
    settings = None


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


# Comprehensive sensitive field patterns to redact in logs
SENSITIVE_FIELDS = {
    'authorization', 'token', 'password', 'secret', 'key',
    'api_key', 'private_key', 'access_token', 'refresh_token',
    'bearer', 'auth', 'credential', 'credentials', 'session',
    'session_token', 'csrf_token', 'jwt', 'oauth_token',
    'client_secret', 'client_id', 'signing_key', 'encryption_key',
    'database_url', 'connection_string', 'db_password', 'redis_url',
    'aws_access_key', 'aws_secret_key', 'azure_key', 'gcp_key',
    'webhook_secret', 'webhook_signature', 'github_token',
    'gitlab_token', 'glm_api_key', 'slack_token', 'discord_token'
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
# Sensitive Data Redaction Classes
# ============================================================================

class RedactionLevel(Enum):
    """Different levels of data redaction for security."""
    NONE = "none"          # No redaction
    BASIC = "basic"        # Basic field name matching
    STANDARD = "standard"  # Pattern matching for common formats
    AGGRESSIVE = "aggressive"  # Aggressive pattern detection


class SensitiveDataRedactor:
    """
    Comprehensive sensitive data redaction system.
    
    Provides multi-level redaction of sensitive information including:
    - Field name-based redaction
    - Pattern-based detection for common sensitive data formats
    - Token and API key detection
    - URL and connection string redaction
    - Configurable redaction levels
    """
    
    def __init__(self, level: RedactionLevel = RedactionLevel.STANDARD):
        """
        Initialize the redactor with specified level.
        
        Args:
            level: Redaction level to apply
        """
        self.level = level
        self.redaction_placeholder = "***REDACTED***"
        self.hash_placeholder = "***HASH:{hash}***"
        self._compile_patterns()
    
    def _compile_patterns(self) -> None:
        """Compile regex patterns for sensitive data detection."""
        self.patterns: List[Pattern] = []
        
        if self.level in [RedactionLevel.STANDARD, RedactionLevel.AGGRESSIVE]:
            # Standard patterns for common sensitive data formats
            
            # API keys (alphanumeric with various lengths)
            self.patterns.extend([
                # Generic API keys
                re.compile(r'(?i)(api[_-]?key["\s]*[:=]["\s]*)([a-zA-Z0-9_\-]+)["\s]*', re.IGNORECASE),
                re.compile(r'(?i)(token["\s]*[:=]["\s]*)([a-zA-Z0-9_\-]{20,})["\s]*', re.IGNORECASE),
                # Bearer tokens - simple and reliable pattern
                re.compile(r'(?i)(bearer\s+)([a-zA-Z0-9_\-\.]{8,})', re.IGNORECASE),
                # Authorization headers
                re.compile(r'(?i)(authorization["\s]*[:=]["\s]*bearer\s+)([a-zA-Z0-9_\-\.]{20,})["\s]*', re.IGNORECASE),
                # JWT tokens (header.payload.signature format) - more specific
                re.compile(r'([a-zA-Z0-9_\-]{10,})\.([a-zA-Z0-9_\-]{10,})\.([a-zA-Z0-9_\-]{10,})'),
                # Base64 encoded data (potential keys)
                re.compile(r'(?i)(["\s]*)([A-Za-z0-9+/]{40,}={0,2})["\s]*', re.IGNORECASE),
            ])
            
            # URL-based sensitive data
            self.patterns.extend([
                # Database URLs with passwords
                re.compile(r'(?i)(postgresql|mysql|mongodb|redis)://[^:\s]+:([^@\s]+)@', re.IGNORECASE),
                # URLs with API keys in query parameters
                re.compile(r'(?i)[?&](api[_-]?key|token|access[_-]?token|secret)=([^&\s]+)', re.IGNORECASE),
                # Generic URLs with sensitive paths
                re.compile(r'(?i)(https?://[^/\s]+/)(api|admin|private|secure)/([^?\s]*)', re.IGNORECASE),
            ])
            
            # AWS keys and signatures
            self.patterns.extend([
                re.compile(r'(?i)(aws[_-]?access[_-]?key[_-]?id["\s]*[:=]["\s]*)([A-Z0-9]{20})["\s]*', re.IGNORECASE),
                re.compile(r'(?i)(aws[_-]?secret[_-]?access[_-]?key["\s]*[:=]["\s]*)([a-zA-Z0-9/+=]{40})["\s]*', re.IGNORECASE),
                re.compile(r'(?i)(x-amz-signature["\s]*[:=]["\s]*)([a-f0-9]{64})["\s]*', re.IGNORECASE),
            ])
        
        if self.level == RedactionLevel.AGGRESSIVE:
            # Aggressive patterns - more thorough but may have false positives
            
            # Generic hexadecimal strings (potential keys/hashes)
            self.patterns.extend([
                re.compile(r'(?i)(["\s]*)([a-f0-9]{32,64})["\s]*', re.IGNORECASE),
                # UUIDs (potential session IDs or tokens)
                re.compile(r'(?:^|\s)([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})(?:\s|$)', re.IGNORECASE),
                # Long alphanumeric strings (potential tokens)
                re.compile(r'(?i)(["\s]*)([a-zA-Z0-9]{32,})["\s]*', re.IGNORECASE),
            ])
    
    def redact_dict(self, data: Dict[str, Any], preserve_length: bool = False) -> Dict[str, Any]:
        """
        Recursively redact sensitive data in a dictionary.
        
        Args:
            data: Dictionary to redact
            preserve_length: Whether to preserve data length in redaction
            
        Returns:
            Dictionary with sensitive data redacted
        """
        if not isinstance(data, dict):
            return data
        
        redacted = {}
        for key, value in data.items():
            # Keep the original key, only redact the value if needed
            redacted_value = self._redact_value(key, value, preserve_length)
            redacted[key] = redacted_value
        
        return redacted
    
    def redact_string(self, text: str) -> str:
        """
        Redact sensitive information from a string.
        
        Args:
            text: String to redact
            
        Returns:
            Redacted string
        """
        if not isinstance(text, str):
            return text
        
        redacted_text = text
        
        # Apply pattern-based redaction
        for pattern in self.patterns:
            if self.level == RedactionLevel.AGGRESSIVE:
                # For aggressive mode, use hash to preserve some identification
                def replacement_func(match):
                    groups = match.groups()
                    if len(groups) >= 2:
                        prefix = groups[0]
                        sensitive_value = groups[-1]  # Get last group (the actual value)
                        hash_value = hashlib.sha256(sensitive_value.encode()).hexdigest()[:8]
                        return f"{prefix}{self.hash_placeholder.format(hash=hash_value)}"
                    elif len(groups) == 1:
                        # Single group (like the Bearer pattern that uses non-capturing group)
                        return self.hash_placeholder.format(hash=hashlib.sha256(groups[0].encode()).hexdigest()[:8])
                    else:
                        # Fallback for patterns without clear groups
                        return self.redaction_placeholder
                
                redacted_text = pattern.sub(replacement_func, redacted_text)
            else:
                # For standard mode, simple replacement
                def simple_replacement(match):
                    groups = match.groups()
                    if len(groups) >= 1:
                        prefix = groups[0]
                        return f"{prefix}{self.redaction_placeholder}"
                    else:
                        return self.redaction_placeholder
                
                redacted_text = pattern.sub(simple_replacement, redacted_text)
        
        return redacted_text
    
    def _redact_field_name(self, field_name: str) -> str:
        """
        Check if field name itself is sensitive and redact if needed.
        
        Args:
            field_name: Field name to check
            
        Returns:
            Original field name or redacted version
        """
        # Only redact the field name if it's extremely sensitive (like password in field name)
        # Most of the time we want to keep field names for debugging but redact values
        return field_name
    
    def _redact_value(self, key: str, value: Any, preserve_length: bool = False) -> Any:
        """
        Redact a value based on its key and content.
        
        Args:
            key: The field key
            value: The value to potentially redact
            preserve_length: Whether to preserve data length
            
        Returns:
            Original value or redacted version
        """
        # Skip null values
        if value is None:
            return value
        
        # Handle nested structures
        if isinstance(value, dict):
            return self.redact_dict(value, preserve_length)
        elif isinstance(value, list):
            return [self._redact_value(f"{key}[]", item, preserve_length) for item in value]
        elif isinstance(value, tuple):
            return tuple(self._redact_value(f"{key}[]", item, preserve_length) for item in value)
        
        # Handle strings
        if isinstance(value, str):
            # Check if key name indicates sensitive data
            if key.lower() in SENSITIVE_FIELDS or any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                if preserve_length and len(value) > 0:
                    return self.redaction_placeholder[:len(value)]
                return self.redaction_placeholder
            
            # Apply pattern-based redaction
            return self.redact_string(value)
        
        # For non-string values with sensitive keys
        if key.lower() in SENSITIVE_FIELDS:
            return self.redaction_placeholder
        
        return value
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about redaction patterns.
        
        Returns:
            Dictionary with redaction statistics
        """
        return {
            "redaction_level": self.level.value,
            "patterns_count": len(self.patterns),
            "sensitive_fields_count": len(SENSITIVE_FIELDS),
            "placeholder": self.redaction_placeholder
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
        if settings and settings.project_id:
            log_entry["project_id"] = settings.project_id
        if settings and settings.mr_iid:
            log_entry["mr_iid"] = settings.mr_iid
    
    def _add_extra_fields(self, log_entry: Dict[str, Any], record: logging.LogRecord) -> None:
        """Add extra fields from the record while excluding standard fields."""
        for key, value in record.__dict__.items():
            if key not in STANDARD_LOG_FIELDS:
                # Apply enhanced redaction to extra fields
                redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
                log_entry[key] = redactor._redact_value(key, value)
    
    def _add_exception_info(self, log_entry: Dict[str, Any], record: logging.LogRecord) -> None:
        """Add exception information if present in the record."""
        if record.exc_info:
            exception_str = self.formatException(record.exc_info)
            # Apply redaction to exception messages too (they might contain sensitive data)
            redactor = SensitiveDataRedactor(RedactionLevel.STANDARD)
            log_entry["exception"] = redactor.redact_string(exception_str)


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
        if settings and settings.project_id:
            context_parts.append(f"project={settings.project_id}")
        if settings and settings.mr_iid:
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
        record.project_id = settings.project_id if settings else None
        record.mr_iid = settings.mr_iid if settings else None
        return True


class SensitiveDataFilter(logging.Filter):
    """
    Advanced filter to sanitize sensitive data in log records.
    
    Automatically redacts sensitive information from log messages
    and extra fields using comprehensive pattern matching and
    configurable redaction levels.
    """
    
    def __init__(
        self, 
        redaction_level: Union[RedactionLevel, str] = RedactionLevel.STANDARD,
        preserve_length: bool = False
    ):
        """
        Initialize sensitive data filter.
        
        Args:
            redaction_level: Level of redaction to apply
            preserve_length: Whether to preserve original data length in redaction
        """
        super().__init__()
        
        # Convert string to enum if needed
        if isinstance(redaction_level, str):
            redaction_level = RedactionLevel(redaction_level.lower())
        
        self.redactor = SensitiveDataRedactor(redaction_level)
        self.preserve_length = preserve_length
        self.redaction_stats = {
            "records_processed": 0,
            "fields_redacted": 0,
            "patterns_matched": 0
        }
    
    def filter(self, record: logging.LogRecord) -> bool:
        """
        Sanitize sensitive data in the log record.
        
        Args:
            record: The log record to sanitize
            
        Returns:
            Always returns True to allow the record through
        """
        self.redaction_stats["records_processed"] += 1
        
        # Sanitize the message
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            original_msg = record.msg
            record.msg = self.redactor.redact_string(record.msg)
            if original_msg != record.msg:
                self.redaction_stats["fields_redacted"] += 1
        
        # Sanitize extra fields
        for key in list(record.__dict__.keys()):
            if key.lower() in SENSITIVE_FIELDS or any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
                original_value = getattr(record, key)
                redacted_value = self.redactor._redact_value(key, original_value, self.preserve_length)
                setattr(record, key, redacted_value)
                
                if original_value != redacted_value:
                    self.redaction_stats["fields_redacted"] += 1
                    self.redaction_stats["patterns_matched"] += 1
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Get redaction statistics.
        
        Returns:
            Dictionary with redaction statistics
        """
        stats = self.redactor.get_stats().copy()
        stats.update(self.redaction_stats)
        return stats
    
    def reset_stats(self) -> None:
        """Reset redaction statistics."""
        self.redaction_stats = {
            "records_processed": 0,
            "fields_redacted": 0,
            "patterns_matched": 0
        }


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
    redaction_level: Union[RedactionLevel, str] = RedactionLevel.STANDARD,
    preserve_sensitive_length: bool = False,
    custom_format_string: Optional[str] = None
) -> logging.Logger:
    """
    Set up comprehensive logging configuration with advanced sensitive data protection.
    
    Configures the root logger with appropriate handlers, formatters,
    and filters. Supports both JSON and text output formats with optional
    file logging and configurable sensitive data redaction levels.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format_type: Log format ('json' or 'text')
        log_file: Optional log file path
        use_colors: Whether to use colors in text output (auto-detected if None)
        sanitize_sensitive_data: Whether to filter sensitive information
        redaction_level: Level of sensitive data redaction (none, basic, standard, aggressive)
        preserve_sensitive_length: Whether to preserve original data length in redaction
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
        ...     format_type="json",
        ...     log_file="/var/log/app.log",
        ...     sanitize_sensitive_data=True,
        ...     redaction_level="standard"
        ... )
    """
    # Use settings defaults if not provided
    level_str = str(level) if level else (settings.log_level if settings else "INFO")
    format_str = str(format_type) if format_type else (settings.log_format if settings else "text")
    log_file_path = log_file or (settings.log_file if settings else None)
    
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
    
    # Convert string to enum if needed
    if isinstance(redaction_level, str):
        redaction_level = RedactionLevel(redaction_level.lower())
    
    # Create filters
    filters: List[logging.Filter] = [ContextFilter()]
    if sanitize_sensitive_data:
        filters.append(SensitiveDataFilter(
            redaction_level=redaction_level,
            preserve_length=preserve_sensitive_length
        ))
    
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
    
    # Also add filters to the root logger itself
    for filter_obj in filters:
        logger.addFilter(filter_obj)
    
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
    """Specialized logger for API interactions with comprehensive redaction."""
    
    def __init__(self, logger_name: str = "api", redaction_level: RedactionLevel = RedactionLevel.STANDARD):
        """
        Initialize API logger.
        
        Args:
            logger_name: Name for the logger
            redaction_level: Level of redaction to apply to API data
        """
        self.logger = get_logger(logger_name)
        self.redactor = SensitiveDataRedactor(redaction_level)
    
    def log_request(
        self,
        api_name: str,
        method: str,
        url: str,
        headers: Dict[str, str],
        body: Optional[Dict[str, Any]] = None
    ):
        """
        Log an API request with comprehensive sensitive data redaction.
        
        Args:
            api_name: Name of the API service
            method: HTTP method
            url: Request URL
            headers: Request headers (will be redacted)
            body: Optional request body (will be redacted)
        """
        # Apply comprehensive redaction to headers
        sanitized_headers = self.redactor.redact_dict(headers)
        
        # Redact URL to remove sensitive query parameters
        sanitized_url = self.redactor.redact_string(url)
        
        self.logger.info(
            f"API Request: {method} {sanitized_url}",
            extra={
                "api_name": api_name,
                "method": method,
                "url": sanitized_url,
                "headers": sanitized_headers,
                "has_body": body is not None
            }
        )
        
        if body and self.logger.isEnabledFor(logging.DEBUG):
            # Apply redaction to request body
            sanitized_body = self.redactor.redact_dict(body) if isinstance(body, dict) else self.redactor.redact_string(str(body))
            
            self.logger.debug(
                f"API Request Body: {method} {sanitized_url}",
                extra={
                    "api_name": api_name,
                    "method": method,
                    "url": sanitized_url,
                    "body": sanitized_body
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
        """
        Log an API response with sensitive data redaction.
        
        Args:
            api_name: Name of the API service
            method: HTTP method
            url: Request URL
            status_code: HTTP status code
            headers: Response headers (will be redacted if needed)
            body: Optional response body (will be redacted)
            response_time_ms: Optional response time in milliseconds
        """
        # Redact URL to remove sensitive query parameters
        sanitized_url = self.redactor.redact_string(url)
        
        # Apply redaction to response headers
        sanitized_headers = self.redactor.redact_dict(headers)
        
        self.logger.info(
            f"API Response: {method} {sanitized_url} - {status_code}",
            extra={
                "api_name": api_name,
                "method": method,
                "url": sanitized_url,
                "status_code": status_code,
                "headers": sanitized_headers,
                "response_time_ms": response_time_ms
            }
        )
        
        if body and self.logger.isEnabledFor(logging.DEBUG):
            # Apply redaction to response body
            sanitized_body = self.redactor.redact_dict(body) if isinstance(body, dict) else self.redactor.redact_string(str(body))
            
            self.logger.debug(
                f"API Response Body: {method} {sanitized_url}",
                extra={
                    "api_name": api_name,
                    "method": method,
                    "url": sanitized_url,
                    "body": sanitized_body
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
        """
        Log an API error with sensitive data redaction.
        
        Args:
            api_name: Name of the API service
            method: HTTP method
            url: Request URL
            error: Exception that occurred
            status_code: Optional HTTP status code
            response_body: Optional response body (will be redacted)
        """
        # Redact URL to remove sensitive query parameters
        sanitized_url = self.redactor.redact_string(url)
        
        # Redact error message (it might contain sensitive data)
        error_message = self.redactor.redact_string(str(error))
        
        error_extra = {
            "api_name": api_name,
            "method": method,
            "url": sanitized_url,
            "status_code": status_code,
            "error_type": type(error).__name__,
            "error_message": error_message,
            "has_response_body": response_body is not None
        }
        
        # Add redacted response body if available
        if response_body and self.logger.isEnabledFor(logging.DEBUG):
            sanitized_body = self.redactor.redact_dict(response_body) if isinstance(response_body, dict) else self.redactor.redact_string(str(response_body))
            error_extra["response_body"] = sanitized_body
        
        self.logger.error(
            f"API Error: {method} {sanitized_url} - {error_message}",
            extra=error_extra,
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


# Initialize logging with default security settings
# Use standard redaction for production safety
setup_logging(
    sanitize_sensitive_data=True,
    redaction_level=RedactionLevel.STANDARD,
    preserve_sensitive_length=False
)

# Create specialized loggers with enhanced security
api_logger = APILogger(redaction_level=RedactionLevel.STANDARD)
review_logger = ReviewLogger()

# Fallback functions for import failures
def get_fallback_logger(name: str) -> logging.Logger:
    """
    Fallback logger function for when imports fail.
    
    This provides a basic logger that can be used when main
    logging infrastructure is not available.
    
    Args:
        name: Logger name
        
    Returns:
        Basic logger instance
    """
    import logging
    return logging.getLogger(name)


def get_fallback_setup_logging(level: str = "INFO", format_type: str = "text", log_file: Optional[str] = None) -> logging.Logger:
    """
    Fallback setup_logging function for when imports fail.
    
    This provides basic logging setup when main logging
    infrastructure is not available.
    
    Args:
        level: Logging level
        format_type: Log format (ignored in fallback)
        log_file: Optional log file path
        
    Returns:
        Basic logger instance
    """
    import logging
    log_level = getattr(logging, level.upper(), logging.INFO)
    logging.basicConfig(level=log_level)
    return logging.getLogger()


# Export the main logger function
__all__ = [
    "setup_logging",
    "get_logger",
    "get_fallback_logger",
    "get_fallback_setup_logging",
    "APILogger",
    "ReviewLogger",
    "api_logger",
    "review_logger"
]