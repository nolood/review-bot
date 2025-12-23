#!/usr/bin/env python3
"""
GLM Code Review Bot - Main Entry Point

This script orchestrates the code review process by integrating:
- GitLab API client for fetching MR details and diffs
- GLM client for code analysis
- Diff parser for processing and chunking changes
- Comment publisher for structured feedback
- Comprehensive error handling and logging
"""

import argparse
import fnmatch
import logging
import os
import sys
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple, Type, Protocol, cast
from dotenv import load_dotenv

# Load environment variables from .env file at startup
load_dotenv()

# ============================================================================
# PROTOCOL DEFINITIONS
# ============================================================================

class LoggerProtocol(Protocol):
    """Protocol for logger interface."""
    def debug(self, msg: str, **kwargs) -> None: ...
    def info(self, msg: str, **kwargs) -> None: ...
    def warning(self, msg: str, **kwargs) -> None: ...
    def error(self, msg: str, **kwargs) -> None: ...
    def exception(self, msg: str, **kwargs) -> None: ...


class SettingsProtocol(Protocol):
    """Protocol for settings interface."""
    gitlab_token: str
    gitlab_api_url: str
    project_id: str
    mr_iid: str
    glm_api_key: str
    glm_api_url: str
    glm_model: str
    glm_temperature: float
    glm_max_tokens: int
    max_diff_size: int
    api_request_delay: float
    max_retries: int
    retry_delay: float
    retry_backoff_factor: float
    log_level: str
    log_format: str
    log_file: Optional[str]
    ignore_file_patterns: List[str]
    prioritize_file_patterns: List[str]
    
    def is_file_ignored(self, file_path: str) -> bool: ...


class ClientProtocol(Protocol):
    """Protocol for client interfaces."""
    def __init__(self, **kwargs) -> None: ...
    def get_merge_request_details(self) -> Dict[str, Any]: ...
    def get_merge_request_diff(self) -> str: ...
    def analyze_code(self, diff_content: str, custom_prompt: Optional[str], review_type: 'ReviewType') -> Dict[str, Any]: ...

# ============================================================================
# APPLICATION CONFIGURATION
# ============================================================================

class AppConfig:
    """Centralized application configuration constants."""
    
    # API Configuration
    GLM_API_URL = "https://api.z.ai/api/paas/v4/chat/completions"
    GITLAB_API_URL = "https://gitlab.com/api/v4"
    GLM_MODEL = "glm-4"
    MAX_DIFF_SIZE = 50000
    MAX_TOKENS = 4000
    TEMPERATURE = 0.3
    API_REQUEST_DELAY = 0.5
    MAX_RETRIES = 3
    RETRY_DELAY = 1.0
    RETRY_BACKOFF_FACTOR = 2.0
    
    # Logging Configuration
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "text"
    
    # File Pattern Configuration
    IGNORE_PATTERNS = [
        "*.min.js", "*.min.css", "*.css.map", "*.js.map", 
        "package-lock.json", "yarn.lock", "*.png", "*.jpg", 
        "*.jpeg", "*.gif", "*.pdf", "*.zip"
    ]
    PRIORITIZE_PATTERNS = [
        "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", 
        "*.java", "*.go", "*.rs", "*.cpp", "*.c", "*.h"
    ]
    
    # Environment Variable Names
    GLM_API_KEY_VAR = "GLM_API_KEY"
    GITLAB_TOKEN_VAR = "GITLAB_TOKEN"
    PROJECT_ID_VAR = "CI_PROJECT_ID"
    MR_IID_VAR = "CI_MERGE_REQUEST_IID"
    GLM_API_URL_VAR = "GLM_API_URL"
    GITLAB_API_URL_VAR = "GITLAB_API_URL"
    
    # Exit Codes
    EXIT_SUCCESS = 0
    EXIT_INTERRUPT = 130
    EXIT_GENERAL_ERROR = 1
    
    # Required Environment Variables
    REQUIRED_VARS_DRY_RUN = [GLM_API_KEY_VAR]
    REQUIRED_VARS_FULL = [GLM_API_KEY_VAR, GITLAB_TOKEN_VAR, PROJECT_ID_VAR, MR_IID_VAR]


# Type Aliases
ProcessingStats = Dict[str, Any]
JSONValue = Union[str, int, float, bool, None, Dict[str, Any], List[Any]]

# ============================================================================
# FALLBACK IMPLEMENTATIONS
# ============================================================================

class ReviewType(str, Enum):
    """Enum for different types of code reviews."""
    GENERAL = "general"
    SECURITY = "security"
    PERFORMANCE = "performance"


class ReviewBotError(Exception):
    """Base exception for review bot errors."""
    pass


class ConfigurationError(ReviewBotError):
    """Exception for configuration-related errors."""
    pass


class MockSettings:
    """Mock settings implementation for fallback mode."""
    
    def __init__(self):
        # Initialize all attributes with defaults
        self.gitlab_token: str = os.getenv(AppConfig.GITLAB_TOKEN_VAR, "")
        self.gitlab_api_url: str = os.getenv(AppConfig.GITLAB_API_URL_VAR, AppConfig.GITLAB_API_URL)
        self.project_id: str = os.getenv(AppConfig.PROJECT_ID_VAR, "")
        self.mr_iid: str = os.getenv(AppConfig.MR_IID_VAR, "")
        self.glm_api_key: str = os.getenv(AppConfig.GLM_API_KEY_VAR, "")
        self.glm_api_url: str = os.getenv(AppConfig.GLM_API_URL_VAR, AppConfig.GLM_API_URL)
        self.glm_model: str = AppConfig.GLM_MODEL
        self.glm_temperature: float = AppConfig.TEMPERATURE
        self.glm_max_tokens: int = AppConfig.MAX_TOKENS
        self.max_diff_size: int = AppConfig.MAX_DIFF_SIZE
        self.api_request_delay: float = AppConfig.API_REQUEST_DELAY
        self.max_retries: int = AppConfig.MAX_RETRIES
        self.retry_delay: float = AppConfig.RETRY_DELAY
        self.retry_backoff_factor: float = AppConfig.RETRY_BACKOFF_FACTOR
        self.log_level: str = AppConfig.LOG_LEVEL
        self.log_format: str = AppConfig.LOG_FORMAT
        self.log_file: Optional[str] = None
        self.ignore_file_patterns: List[str] = AppConfig.IGNORE_PATTERNS.copy()
        self.prioritize_file_patterns: List[str] = AppConfig.PRIORITIZE_PATTERNS.copy()
    
    def is_file_ignored(self, file_path: str) -> bool:
        """Check if a file should be ignored based on patterns."""
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_file_patterns)


class MockLogger:
    """Mock logger implementation for fallback mode."""
    
    def __init__(self, name: str):
        self._logger = logging.getLogger(name)
    
    def debug(self, msg: str, **kwargs) -> None:
        self._logger.debug(msg, **kwargs)
    
    def info(self, msg: str, **kwargs) -> None:
        self._logger.info(msg, **kwargs)
    
    def warning(self, msg: str, **kwargs) -> None:
        self._logger.warning(msg, **kwargs)
    
    def error(self, msg: str, **kwargs) -> None:
        self._logger.error(msg, **kwargs)
    
    def exception(self, msg: str, **kwargs) -> None:
        self._logger.exception(msg, **kwargs)


# Initialize fallback implementations
settings = cast(SettingsProtocol, MockSettings())


def setup_logging(level: str = AppConfig.LOG_LEVEL, format_type: str = AppConfig.LOG_FORMAT, log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging with the specified parameters."""
    from src.utils.logger import get_fallback_setup_logging
    return get_fallback_setup_logging(level, format_type, log_file)


def get_logger(name: str) -> LoggerProtocol:
    """Get a logger instance with the specified name."""
    from src.utils.logger import get_fallback_logger
    return MockLogger(name)  # Keep MockLogger for protocol compatibility


class GitLabClient:
    """Mock GitLab client for fallback mode."""
    def get_merge_request_details(self) -> Dict[str, Any]:
        return {"id": settings.project_id, "iid": settings.mr_iid}
    
    def get_merge_request_diff(self) -> str:
        return "mock diff content"


class GLMClient:
    """Mock GLM client for fallback mode."""
    def __init__(self, **kwargs):
        pass
    
    def analyze_code(self, diff_content: str, custom_prompt: Optional[str], review_type: ReviewType) -> Dict[str, Any]:
        return {"comments": [], "usage": {"total_tokens": 0}}


class DiffParser:
    """Mock diff parser for fallback mode."""
    def __init__(self, max_chunk_tokens: int = AppConfig.MAX_DIFF_SIZE):
        self.max_chunk_tokens = max_chunk_tokens
    
    def parse_gitlab_diff(self, gitlab_diffs: List[Dict[str, Any]]) -> List[Any]:
        return []
    
    def chunk_large_diff(self, file_diffs: List[Any]) -> List[Any]:
        return []
    
    def get_diff_summary(self, file_diffs: List[Any]) -> Dict[str, Any]:
        return {"total_files": 0, "total_lines": 0}


class CommentPublisher:
    """Mock comment publisher for fallback mode."""
    def __init__(self, gitlab_client):
        self.gitlab_client = gitlab_client
    
    def format_comments(self, glm_response: Dict[str, Any]) -> Any:
        class MockCommentBatch:
            summary_comment = None
            file_comments = []
            inline_comments = []
        return MockCommentBatch()
    
    def publish_review_summary(self, comment: Any, mr_details: Dict[str, Any]) -> None:
        pass
    
    def publish_file_comments(self, comments: List[Any], mr_details: Dict[str, Any]) -> None:
        pass


# ============================================================================
# IMPORT REAL IMPLEMENTATIONS IF AVAILABLE
# ============================================================================

# Add src directory to Python path for imports
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Import from local modules with proper error handling
import_successful = False
try:
    # Use relative imports with proper error handling
    import importlib
    
    # Import settings
    config_settings = importlib.import_module('config.settings')
    settings = cast(SettingsProtocol, config_settings.settings)
    
    # Import prompts
    config_prompts = importlib.import_module('config.prompts')
    ReviewType = config_prompts.ReviewType
    
    # Import clients
    gitlab_client_module = importlib.import_module('gitlab_client')
    GitLabClient = gitlab_client_module.GitLabClient
    
    glm_client_module = importlib.import_module('glm_client')
    GLMClient = glm_client_module.GLMClient
    
    diff_parser_module = importlib.import_module('diff_parser')
    DiffParser = diff_parser_module.DiffParser
    
    comment_publisher_module = importlib.import_module('comment_publisher')
    CommentPublisher = comment_publisher_module.CommentPublisher

    line_code_mapper_module = importlib.import_module('line_code_mapper')
    LinePositionValidator = line_code_mapper_module.LinePositionValidator

    # Import utils
    logger_module = importlib.import_module('utils.logger')
    setup_logging = logger_module.setup_logging
    
    # Create a wrapper for get_logger that returns a LoggerProtocol compatible object
    original_get_logger = logger_module.get_logger
    def wrapped_get_logger(name: str) -> LoggerProtocol:
        return cast(LoggerProtocol, original_get_logger(name))
    get_logger = wrapped_get_logger
    
    exceptions_module = importlib.import_module('utils.exceptions')
    ReviewBotError = exceptions_module.ReviewBotError
    ConfigurationError = exceptions_module.ConfigurationError
    GLMAPIError = exceptions_module.GLMAPIError
    GitLabAPIError = exceptions_module.GitLabAPIError
    DiffParsingError = exceptions_module.DiffParsingError
    CommentPublishError = exceptions_module.CommentPublishError
    RetryExhaustedError = exceptions_module.RetryExhaustedError
    
    import_successful = True
    
except ImportError as e:
    # Fallback implementations already defined above
    print(f"Warning: Could not import from src modules: {e}, using fallback implementations")
    import_successful = False

# Create a proper wrapper logger that implements the LoggerProtocol
def create_logger(name: str) -> LoggerProtocol:
    """Create a logger that implements LoggerProtocol."""
    logger = get_logger(name)
    
    # If logger already implements LoggerProtocol, return it directly
    if hasattr(logger, 'debug') and hasattr(logger, 'info'):
        try:
            # Test if the signature matches
            logger.debug("test", extra={})
            return logger
        except:
            pass
    
    # Otherwise, wrap the logger to match the protocol
    class LoggerWrapper:
        def __init__(self, wrapped_logger):
            self._logger = wrapped_logger
            
        def debug(self, msg: str, **kwargs) -> None:
            self._logger.debug(msg, **kwargs)
            
        def info(self, msg: str, **kwargs) -> None:
            self._logger.info(msg, **kwargs)
            
        def warning(self, msg: str, **kwargs) -> None:
            self._logger.warning(msg, **kwargs)
            
        def error(self, msg: str, **kwargs) -> None:
            self._logger.error(msg, **kwargs)
            
        def exception(self, msg: str, **kwargs) -> None:
            self._logger.exception(msg, **kwargs)
    
    return LoggerWrapper(logger)

# Override get_logger to return a proper LoggerProtocol
def get_logger(name: str) -> LoggerProtocol:
    """Get a logger that implements the LoggerProtocol."""
    return create_logger(name)

# Define fallback implementations first
class ReviewType(str, Enum):
    """Enum for different types of code reviews."""
    GENERAL = "general"
    SECURITY = "security"
    PERFORMANCE = "performance"


class ReviewBotError(Exception):
    """Base exception for review bot errors."""
    pass


class ConfigurationError(ReviewBotError):
    """Exception for configuration-related errors."""
    pass


class MockSettings:
    """Mock settings implementation for fallback mode."""
    
    def __init__(self):
        # Initialize all attributes with defaults
        self.gitlab_token: str = os.getenv(AppConfig.GITLAB_TOKEN_VAR, "")
        self.gitlab_api_url: str = os.getenv(AppConfig.GITLAB_API_URL_VAR, AppConfig.GITLAB_API_URL)
        self.project_id: str = os.getenv(AppConfig.PROJECT_ID_VAR, "")
        self.mr_iid: str = os.getenv(AppConfig.MR_IID_VAR, "")
        self.glm_api_key: str = os.getenv(AppConfig.GLM_API_KEY_VAR, "")
        self.glm_api_url: str = os.getenv(AppConfig.GLM_API_URL_VAR, AppConfig.GLM_API_URL)
        self.glm_model: str = AppConfig.GLM_MODEL
        self.glm_temperature: float = AppConfig.TEMPERATURE
        self.glm_max_tokens: int = AppConfig.MAX_TOKENS
        self.max_diff_size: int = AppConfig.MAX_DIFF_SIZE
        self.api_request_delay: float = AppConfig.API_REQUEST_DELAY
        self.max_retries: int = AppConfig.MAX_RETRIES
        self.retry_delay: float = AppConfig.RETRY_DELAY
        self.retry_backoff_factor: float = AppConfig.RETRY_BACKOFF_FACTOR
        self.log_level: str = AppConfig.LOG_LEVEL
        self.log_format: str = AppConfig.LOG_FORMAT
        self.log_file: Optional[str] = None
        self.ignore_file_patterns: List[str] = AppConfig.IGNORE_PATTERNS.copy()
        self.prioritize_file_patterns: List[str] = AppConfig.PRIORITIZE_PATTERNS.copy()
    
    def is_file_ignored(self, file_path: str) -> bool:
        """Check if a file should be ignored based on patterns."""
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_file_patterns)


# Initialize fallback implementations - will be replaced if imports succeed
settings: SettingsProtocol = MockSettings()  # type: ignore


# Add src directory to Python path for imports
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

# Import from local modules with proper error handling
import_successful = False
try:
    # Use absolute imports with proper package names
    import src.config.settings as config_settings
    import src.config.prompts as config_prompts
    import src.gitlab_client as gitlab_client_module
    import src.glm_client as glm_client_module
    import src.diff_parser as diff_parser_module
    import src.comment_publisher as comment_publisher_module
    import src.line_code_mapper as line_code_mapper_module
    import src.utils.logger as logger_module
    import src.utils.exceptions as exceptions_module

    # Use imported implementations
    ReviewType = config_prompts.ReviewType
    settings = config_settings.settings
    GitLabClient = gitlab_client_module.GitLabClient
    GLMClient = glm_client_module.GLMClient
    DiffParser = diff_parser_module.DiffParser
    CommentPublisher = comment_publisher_module.CommentPublisher
    LinePositionValidator = line_code_mapper_module.LinePositionValidator
    setup_logging = logger_module.setup_logging
    get_logger = logger_module.get_logger
    ReviewBotError = exceptions_module.ReviewBotError
    ConfigurationError = exceptions_module.ConfigurationError
    GLMAPIError = exceptions_module.GLMAPIError
    GitLabAPIError = exceptions_module.GitLabAPIError
    DiffParsingError = exceptions_module.DiffParsingError
    CommentPublishError = exceptions_module.CommentPublishError
    RetryExhaustedError = exceptions_module.RetryExhaustedError
    
    import_successful = True
    
except ImportError as e:
    # Fallback implementations already defined above
    print(f"Warning: Could not import from src modules: {e}, using fallback implementations")
    import_successful = False
    
    # Define mock client classes
    class GitLabClient:
        """Mock GitLab client for fallback mode."""
        def get_merge_request_details(self) -> Dict[str, Any]:
            return {"id": settings.project_id, "iid": settings.mr_iid}
        
        def get_merge_request_diff(self) -> str:
            return "mock diff content"
    
    class GLMClient:
        """Mock GLM client for fallback mode."""
        def __init__(self, **kwargs):
            pass
        
        def analyze_code(self, diff_content: str, custom_prompt: Optional[str], review_type: ReviewType) -> Dict[str, Any]:
            return {"comments": [], "usage": {"total_tokens": 0}}
    
    class DiffParser:
        """Mock diff parser for fallback mode."""
        def __init__(self, max_chunk_tokens: int = AppConfig.MAX_DIFF_SIZE):
            self.max_chunk_tokens = max_chunk_tokens
        
        def parse_gitlab_diff(self, gitlab_diffs: List[Dict[str, Any]]) -> List[Any]:
            return []
        
        def chunk_large_diff(self, file_diffs: List[Any]) -> List[Any]:
            return []
        
        def get_diff_summary(self, file_diffs: List[Any]) -> Dict[str, Any]:
            return {"total_files": 0, "total_lines": 0}
    
    class CommentPublisher:
        """Mock comment publisher for fallback mode."""
        def __init__(self, gitlab_client):
            self.gitlab_client = gitlab_client
        
        def format_comments(self, glm_response: Dict[str, Any]) -> Any:
            class MockCommentBatch:
                summary_comment = None
                file_comments = []
                inline_comments = []
            return MockCommentBatch()
        
        def publish_review_summary(self, comment: Any, mr_details: Dict[str, Any]) -> None:
            pass
        
        def publish_file_comments(self, comments: List[Any], mr_details: Dict[str, Any]) -> None:
            pass


@dataclass
class ReviewContext:
    """Context information for the review process."""
    project_id: str
    mr_iid: str
    mr_details: Optional[Dict[str, Any]] = None
    diff_summary: Optional[Dict[str, Any]] = None
    processing_stats: Optional[ProcessingStats] = None
    
    def __post_init__(self) -> None:
        """Initialize processing stats if not provided."""
        if self.processing_stats is None:
            self.processing_stats = {}
    
    def update_processing_stats(self, **kwargs) -> None:
        """Update processing statistics safely."""
        if self.processing_stats is None:
            self.processing_stats = {}
        self.processing_stats.update(kwargs)


class EnvironmentValidator:
    """Utility class for environment validation."""
    
    @staticmethod
    def validate_url(url: str, name: str) -> None:
        """Validate that a URL has proper format."""
        if not url.startswith(("http://", "https://")):
            raise ConfigurationError(f"Invalid {name}: {url}")
    
    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float, name: str) -> None:
        """Validate that a numeric value is within range."""
        if not min_val <= value <= max_val:
            raise ConfigurationError(
                f"Invalid {name}: {value}. Must be between {min_val} and {max_val}"
            )
    
    @staticmethod
    def validate_positive(value: int, name: str) -> None:
        """Validate that a numeric value is positive."""
        if value <= 0:
            raise ConfigurationError(
                f"Invalid {name}: {value}. Must be positive"
            )
    
    @staticmethod
    def get_env_value(var_name: str, settings_obj: SettingsProtocol) -> str:
        """Get environment value from settings or environment."""
        env_mapping = {
            AppConfig.GLM_API_KEY_VAR: "glm_api_key",
            AppConfig.GITLAB_TOKEN_VAR: "gitlab_token",
            AppConfig.PROJECT_ID_VAR: "project_id",
            AppConfig.MR_IID_VAR: "mr_iid"
        }
        
        if var_name in env_mapping and hasattr(settings_obj, env_mapping[var_name]):
            return getattr(settings_obj, env_mapping[var_name])
        return os.getenv(var_name, "")


def validate_environment(dry_run: bool = False) -> bool:
    """
    Validate all required environment variables and settings.
    
    Args:
        dry_run: Whether this is a dry run (relaxes some requirements)
        
    Returns:
        True if validation passes
        
    Raises:
        ConfigurationError: If required settings are missing or invalid
    """
    logger = get_logger("validator")
    validator = EnvironmentValidator()
    
    logger.info("Validating environment and configuration")
    
    try:
        # Determine required variables based on run mode
        required_vars = AppConfig.REQUIRED_VARS_DRY_RUN.copy()
        if not dry_run:
            required_vars.extend(AppConfig.REQUIRED_VARS_FULL[1:])  # Skip GLM_API_KEY as it's already included
        
        # Check for missing variables
        missing_vars = []
        for var in required_vars:
            env_value = validator.get_env_value(var, settings)
            if not env_value:
                missing_vars.append(var)
        
        if missing_vars:
            raise ConfigurationError(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
        
        # Validate temperature range
        if hasattr(settings, 'glm_temperature'):
            validator.validate_range(
                settings.glm_temperature, 0.0, 1.0, "GLM temperature"
            )
        
        # Validate positive values
        if hasattr(settings, 'max_diff_size'):
            validator.validate_positive(settings.max_diff_size, "max_diff_size")
        
        # Validate file patterns
        if hasattr(settings, 'ignore_file_patterns') and not settings.ignore_file_patterns:
            logger.warning("No ignore file patterns configured")
        
        if hasattr(settings, 'prioritize_file_patterns') and not settings.prioritize_file_patterns:
            logger.warning("No prioritize file patterns configured")
        
        # Validate API URLs
        if hasattr(settings, 'gitlab_api_url'):
            validator.validate_url(settings.gitlab_api_url, "GitLab API URL")
        
        if hasattr(settings, 'glm_api_url'):
            validator.validate_url(settings.glm_api_url, "GLM API URL")
        
        logger.info("Environment validation completed successfully")
        return True
        
    except Exception as e:
        logger.error(f"Environment validation failed: {e}")
        raise ConfigurationError(f"Environment validation failed: {e}") from e


class ReviewProcessor:
    """Handles the main review processing logic."""
    
    def __init__(self, settings_obj: SettingsProtocol):
        """Initialize with settings object."""
        self.settings = settings_obj
        self.logger = get_logger("processor")
    
    def _initialize_clients(self) -> Tuple[bool, Dict[str, Any]]:
        """Initialize API clients and return success status and client dict."""
        try:
            gitlab_client = GitLabClient()
            glm_client = GLMClient(
                api_key=getattr(self.settings, 'glm_api_key', os.getenv("GLM_API_KEY", "")),
                api_url=getattr(self.settings, 'glm_api_url', os.getenv("GLM_API_URL", AppConfig.GLM_API_URL)),
                model=getattr(self.settings, 'glm_model', AppConfig.GLM_MODEL),
                temperature=getattr(self.settings, 'glm_temperature', AppConfig.TEMPERATURE),
                max_tokens=getattr(self.settings, 'glm_max_tokens', AppConfig.MAX_TOKENS)
            )
            diff_parser = DiffParser(max_chunk_tokens=getattr(self.settings, 'max_diff_size', AppConfig.MAX_DIFF_SIZE))

            # Create line position validator for validating inline comment positions
            line_position_validator = LinePositionValidator()
            self.logger.info("Line position validator created successfully")

            # Pass the validator to comment publisher
            comment_publisher = CommentPublisher(gitlab_client, line_position_validator)
            self.logger.info("Comment publisher initialized with line position validator")

            clients = {
                "gitlab": gitlab_client,
                "glm": glm_client,
                "diff_parser": diff_parser,
                "comment_publisher": comment_publisher,
                "line_position_validator": line_position_validator
            }
            return True, clients
        except Exception as e:
            self.logger.warning(f"Could not initialize real clients: {e}, using mock implementation")
            return False, {}
    
    def _fetch_mr_data(self, clients: Dict[str, Any], context: ReviewContext) -> Tuple[Optional[List[Any]], Optional[Dict[str, Any]]]:
        """Fetch MR details and diffs."""
        gitlab_client = clients["gitlab"]
        diff_parser = clients["diff_parser"]
        line_position_validator = clients.get("line_position_validator")

        # Fetch MR details
        self.logger.info("Fetching merge request details")
        context.mr_details = gitlab_client.get_merge_request_details()

        # Fetch and parse diffs
        self.logger.info("Fetching and parsing MR diffs")
        diff_data = gitlab_client.get_merge_request_diffs_raw()

        # Build line position mappings for inline comment validation
        if line_position_validator:
            self.logger.info("Building line position mappings for inline comments")
            try:
                line_position_validator.build_mappings_from_diff_data(diff_data)
                self.logger.info(
                    f"Line position mappings built for {len(line_position_validator.file_mappings)} files"
                )
            except Exception as e:
                self.logger.error(f"Failed to build line position mappings: {e}", exc_info=True)
        else:
            self.logger.warning("Line position validator is None - inline comment validation disabled")

        # Parse GitLab diff format (diff_data is already a list of diffs)
        file_diffs = diff_parser.parse_gitlab_diff(diff_data)

        # Generate diff summary if files were found
        if file_diffs:
            context.diff_summary = diff_parser.get_diff_summary(file_diffs)
            self.logger.info("Diff processing completed", extra=context.diff_summary or {})

        return file_diffs, context.diff_summary
    
    def _process_chunks(self, clients: Dict[str, Any], chunks: List[Any], review_type: ReviewType, custom_prompt: Optional[str]) -> Tuple[List[Any], int]:
        """Process diff chunks with GLM analysis."""
        glm_client = clients["glm"]
        all_comments = []
        total_tokens_used = 0
        
        for i, chunk in enumerate(chunks):
            self.logger.info(f"Processing chunk {i+1}/{len(chunks)}")
            
            chunk_start_time = time.time()
            chunk_content = chunk.get_content()
            
            # Analyze with GLM
            glm_response = glm_client.analyze_code(
                diff_content=chunk_content,
                custom_prompt=custom_prompt,
                review_type=review_type
            )
            
            # Extract and store comments
            if "comments" in glm_response:
                all_comments.extend(glm_response["comments"])
            
            # Track token usage
            if "usage" in glm_response:
                total_tokens_used += glm_response["usage"].get("total_tokens", 0)
            
            chunk_time = time.time() - chunk_start_time
            self.logger.info(
                f"Chunk {i+1} processed in {chunk_time:.2f}s",
                extra={
                    "chunk_number": i+1,
                    "chunk_files": len(chunk.files),
                    "chunk_tokens": chunk.estimated_tokens,
                    "processing_time": chunk_time
                }
            )
        
        return all_comments, total_tokens_used
    
    def _publish_comments(self, clients: Dict[str, Any], comments: List[Any], context: ReviewContext, dry_run: bool) -> None:
        """Format and publish comments to GitLab."""
        comment_publisher = clients["comment_publisher"]
        
        self.logger.info(f"Formatting {len(comments)} comments for publication")
        
        # Create mock GLM response for comment formatting
        mock_response = {"comments": comments}
        comment_batch = comment_publisher.format_comments(mock_response)
        
        if not dry_run:
            self.logger.info("Publishing comments to GitLab")
            
            # Publish summary comment if available
            if comment_batch.summary_comment:
                comment_publisher.publish_review_summary(
                    comment_batch.summary_comment,
                    context.mr_details
                )
            
            # Publish file comments
            all_file_comments = comment_batch.file_comments + comment_batch.inline_comments
            if all_file_comments:
                comment_publisher.publish_file_comments(
                    all_file_comments,
                    context.mr_details
                )
            
            context.update_processing_stats(
                summary_published=comment_batch.summary_comment is not None,
                file_comments_published=len(comment_batch.file_comments),
                inline_comments_published=len(comment_batch.inline_comments)
            )
        else:
            self.logger.info(
                "Dry run mode - skipping comment publication",
                extra={
                    "would_publish_summary": comment_batch.summary_comment is not None,
                    "would_publish_file_comments": len(comment_batch.file_comments),
                    "would_publish_inline_comments": len(comment_batch.inline_comments)
                }
            )

            # Print formatted comments preview in dry-run mode
            print("\n" + "="*80)
            print("🔍 DRY RUN MODE - PREVIEW OF COMMENTS THAT WOULD BE PUBLISHED")
            print("="*80)

            if comment_batch.summary_comment:
                print("\n📋 SUMMARY COMMENT:")
                print("-" * 80)
                print(comment_batch.summary_comment)
                print("-" * 80)

            if comment_batch.file_comments:
                print(f"\n📁 FILE COMMENTS ({len(comment_batch.file_comments)}):")
                for i, comment in enumerate(comment_batch.file_comments, 1):
                    print(f"\n--- Comment {i} ---")
                    # FormattedComment is a dataclass, not a dict
                    if hasattr(comment, 'file_path'):
                        print(f"File: {comment.file_path}")
                        if comment.line_number:
                            print(f"Line: {comment.line_number}")
                        print(f"Type: {comment.comment_type.value}")
                        print(f"Severity: {comment.severity.value}")
                        if comment.title:
                            print(f"Title: {comment.title}")
                        print(f"Body:\n{comment.body}")
                    else:
                        print(comment)
                    print("-" * 40)

            if comment_batch.inline_comments:
                print(f"\n💬 INLINE COMMENTS ({len(comment_batch.inline_comments)}):")
                for i, comment in enumerate(comment_batch.inline_comments, 1):
                    print(f"\n--- Inline Comment {i} ---")
                    # FormattedComment is a dataclass, not a dict
                    if hasattr(comment, 'file_path'):
                        print(f"File: {comment.file_path}")
                        if comment.line_number:
                            print(f"Line: {comment.line_number}")
                        print(f"Type: {comment.comment_type.value}")
                        print(f"Severity: {comment.severity.value}")
                        if comment.title:
                            print(f"Title: {comment.title}")
                        print(f"Body:\n{comment.body}")
                    else:
                        print(comment)
                    print("-" * 40)

            if not comment_batch.summary_comment and not comment_batch.file_comments and not comment_batch.inline_comments:
                print("\n⚠️  No comments generated")

            print("\n" + "="*80)
            print("✅ Dry run complete - no comments were published to GitLab")
            print("="*80 + "\n")
    
    def process_merge_request(
        self,
        dry_run: bool = False,
        review_type: ReviewType = ReviewType.GENERAL,
        custom_prompt: Optional[str] = None,
        max_chunks: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Process a single merge request end-to-end.
        
        Args:
            dry_run: Skip actual comment publishing
            review_type: Type of review to perform
            custom_prompt: Custom prompt instructions
            max_chunks: Maximum number of chunks to process
            
        Returns:
            Dictionary with processing results and statistics
            
        Raises:
            ReviewBotError: If processing fails
        """
        start_time = time.time()
        
        # Initialize context
        context = ReviewContext(
            project_id=getattr(self.settings, 'project_id', os.getenv("CI_PROJECT_ID", "")),
            mr_iid=getattr(self.settings, 'mr_iid', os.getenv("CI_MERGE_REQUEST_IID", ""))
        )
        
        try:
            self.logger.info(
                "Starting MR review processing",
                extra={
                    "project_id": context.project_id,
                    "mr_iid": context.mr_iid,
                    "review_type": review_type.value,
                    "dry_run": dry_run
                }
            )
            
            # Initialize clients
            self.logger.info("Initializing API clients")
            use_real_clients, clients = self._initialize_clients()
            
            if use_real_clients:
                # Fetch MR data
                file_diffs, diff_summary = self._fetch_mr_data(clients, context)
                
                if not file_diffs:
                    self.logger.warning("No files to review (all files ignored or empty diff)")
                    return {
                        "status": "success",
                        "message": "No files to review",
                        "processing_time": time.time() - start_time,
                        "stats": context.processing_stats
                    }
                
                # Create diff chunks
                self.logger.info("Creating diff chunks for processing")
                chunks = clients["diff_parser"].chunk_large_diff(file_diffs)
                
                if max_chunks:
                    chunks = chunks[:max_chunks]
                    self.logger.info(f"Limiting to {max_chunks} chunks")
                
                # Process chunks with GLM
                self.logger.info(f"Processing {len(chunks)} chunks with GLM")
                all_comments, total_tokens_used = self._process_chunks(
                    clients, chunks, review_type, custom_prompt
                )
                
                # Update processing stats
                context.update_processing_stats(
                    chunks_processed=len(chunks),
                    total_comments_generated=len(all_comments),
                    total_tokens_used=total_tokens_used,
                    files_reviewed=len(file_diffs)
                )
                
                # Publish comments if any were generated
                if all_comments:
                    self._publish_comments(clients, all_comments, context, dry_run)
                else:
                    self.logger.info("No comments generated from analysis")
            else:
                # Mock implementation for demonstration
                self.logger.info("Using mock implementation for demonstration")
                context.update_processing_stats(
                    chunks_processed=1,
                    total_comments_generated=0,
                    total_tokens_used=0,
                    files_reviewed=0,
                    mock_mode=True
                )
                if dry_run:
                    self.logger.info("Dry run mode - skipping mock comment publication")
            
            # Calculate total processing time
            total_time = time.time() - start_time
            if context.processing_stats:
                context.processing_stats["total_processing_time"] = total_time
            
            self.logger.info(
                "MR review processing completed successfully",
                extra=context.processing_stats or {}
            )
            
            return {
                "status": "success",
                "message": "Review processing completed",
                "processing_time": total_time,
                "stats": context.processing_stats or {},
                "context": context
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"MR review processing failed: {str(e)}"
            
            self.logger.error(
                error_msg,
                extra={
                    "processing_time": processing_time,
                    "error_type": type(e).__name__,
                    "error_details": str(e)
                },
                exc_info=True
            )
            
            # Re-raise as ReviewBotError for consistent error handling
            if isinstance(e, ReviewBotError):
                raise
            else:
                raise ReviewBotError(error_msg) from e


def process_merge_request(
    dry_run: bool = False,
    review_type: ReviewType = ReviewType.GENERAL,
    custom_prompt: Optional[str] = None,
    max_chunks: Optional[int] = None
) -> Dict[str, Any]:
    """
    Process a single merge request end-to-end.
    
    This is a convenience wrapper around ReviewProcessor.process_merge_request.
    
    Args:
        dry_run: Skip actual comment publishing
        review_type: Type of review to perform
        custom_prompt: Custom prompt instructions
        max_chunks: Maximum number of chunks to process
        
    Returns:
        Dictionary with processing results and statistics
        
    Raises:
        ReviewBotError: If processing fails
    """
    processor = ReviewProcessor(settings)  # type: ignore
    return processor.process_merge_request(dry_run, review_type, custom_prompt, max_chunks)


class CLIRunner:
    """Handles command-line interface and execution."""
    
    def __init__(self):
        """Initialize the CLI runner."""
        self.logger: Optional[LoggerProtocol] = None
    
    def _create_parser(self) -> argparse.ArgumentParser:
        """Create and configure the argument parser."""
        parser = argparse.ArgumentParser(
            description="GLM-powered GitLab code review bot",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run general review on current MR
  python review_bot.py
  
  # Run security-focused review
  python review_bot.py --type security
  
  # Run with custom prompt (dry run)
  python review_bot.py --dry-run --custom-prompt "Focus on error handling"
  
  # Limit processing to first 3 chunks
  python review_bot.py --max-chunks 3
            """
        )
        
        parser.add_argument(
            "--type",
            choices=["general", "security", "performance"],
            default="general",
            help="Type of review to perform (default: general)"
        )
        
        parser.add_argument(
            "--custom-prompt",
            type=str,
            help="Custom prompt instructions for the review"
        )
        
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run analysis without publishing comments"
        )
        
        parser.add_argument(
            "--max-chunks",
            type=int,
            help="Maximum number of diff chunks to process"
        )
        
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Override logging level"
        )
        
        parser.add_argument(
            "--log-format",
            choices=["text", "json"],
            help="Override log format"
        )
        
        parser.add_argument(
            "--log-file",
            type=str,
            help="Log to file instead of console"
        )
        
        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="Only validate environment and exit"
        )
        
        return parser
    
    def _setup_logging(self, args: argparse.Namespace) -> bool:
        """Setup logging with command-line overrides."""
        try:
            setup_logging(
                level=args.log_level or getattr(settings, 'log_level', AppConfig.LOG_LEVEL),
                format_type=args.log_format or getattr(settings, 'log_format', AppConfig.LOG_FORMAT),
                log_file=args.log_file or getattr(settings, 'log_file', None)
            )
            self.logger = get_logger("main")
            return True
        except Exception as e:
            print(f"Failed to setup logging: {e}", file=sys.stderr)
            return False
    
    def _print_success_summary(self, result: Dict[str, Any], dry_run: bool) -> None:
        """Print a success summary to stdout for CI/CD integration."""
        print(f"✅ Review completed in {result['processing_time']:.2f}s")
        stats = result["stats"] or {}
        if stats.get("total_comments_generated", 0) > 0:
            print(f"📝 Generated {stats['total_comments_generated']} comments")
            if not dry_run:
                published = stats.get("file_comments_published", 0) + stats.get("inline_comments_published", 0)
                print(f"📤 Published {published} comments")
    
    def run(self, argv: Optional[List[str]] = None) -> int:
        """
        Run the CLI application with the provided arguments.
        
        Args:
            argv: List of command-line arguments (uses sys.argv if None)
            
        Returns:
            Exit code
        """
        parser = self._create_parser()
        args = parser.parse_args(argv)
        
        # Setup logging
        if not self._setup_logging(args):
            return AppConfig.EXIT_GENERAL_ERROR
        
        try:
            # Convert review type string to enum
            review_type = ReviewType(args.type)
            
            # Validate environment
            validate_environment(dry_run=args.dry_run)
            
            if args.validate_only:
                if self.logger:
                    self.logger.info("Environment validation completed successfully")
                return AppConfig.EXIT_SUCCESS
            
            # Process the merge request
            result = process_merge_request(
                dry_run=args.dry_run,
                review_type=review_type,
                custom_prompt=args.custom_prompt,
                max_chunks=args.max_chunks
            )
            
            if result["status"] == "success":
                if self.logger:
                    self.logger.info(
                        "Review bot completed successfully",
                        extra={
                            "processing_time": result["processing_time"],
                            "stats": result["stats"]
                        }
                    )
                
                # Print summary for CI/CD integration
                self._print_success_summary(result, args.dry_run)
                return AppConfig.EXIT_SUCCESS
            else:
                if self.logger:
                    self.logger.error(f"Review processing failed: {result.get('message', 'Unknown error')}")
                return AppConfig.EXIT_GENERAL_ERROR
                
        except KeyboardInterrupt:
            if self.logger:
                self.logger.info("Review processing interrupted by user")
            return AppConfig.EXIT_INTERRUPT
        except ReviewBotError as e:
            if self.logger:
                self.logger.error(f"Review bot error: {e}")
            return AppConfig.EXIT_GENERAL_ERROR
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
            return AppConfig.EXIT_GENERAL_ERROR


def main() -> int:
    """Main entry point for the GLM Code Review Bot."""
    runner = CLIRunner()
    return runner.run()


if __name__ == "__main__":
    sys.exit(main())