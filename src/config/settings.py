"""
Configuration management for the GLM Code Review Bot.

This module uses Pydantic for type-safe configuration management
and environment variable validation.
"""

import os
from typing import Optional, List, Dict, Protocol
from dataclasses import dataclass, field
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


@dataclass
class Settings:
    """
    Application settings loaded from environment variables.
    
    All settings have sensible defaults where applicable and
    are validated on instantiation.
    """
    
    # GitLab Configuration
    gitlab_token: str = field(default_factory=lambda: os.getenv("GITLAB_TOKEN", ""))
    gitlab_api_url: str = field(default="https://gitlab.com/api/v4")
    project_id: str = field(default_factory=lambda: os.getenv("CI_PROJECT_ID", ""))
    mr_iid: str = field(default_factory=lambda: os.getenv("CI_MERGE_REQUEST_IID", ""))
    
    # GLM Configuration
    glm_api_key: str = field(default_factory=lambda: os.getenv("GLM_API_KEY", ""))
    glm_api_url: str = field(default="https://api.z.ai/api/paas/v4/chat/completions")
    glm_model: str = field(default="glm-4")
    glm_temperature: float = field(default=0.3)
    glm_max_tokens: int = field(default=4000)
    
    # Processing Configuration
    max_diff_size: int = field(default=50000)
    max_files_per_comment: int = field(default=10)
    enable_inline_comments: bool = field(default=True)
    
    # Review Configuration
    enable_security_review: bool = field(default=True)
    enable_performance_review: bool = field(default=True)
    min_severity_level: str = field(default="low")
    
    # Rate Limiting
    api_request_delay: float = field(default=0.5)
    max_parallel_requests: int = field(default=3)
    
    # Retry Configuration
    max_retries: int = field(default=3)
    retry_delay: float = field(default=1.0)
    retry_backoff_factor: float = field(default=2.0)
    
    # Logging Configuration
    log_level: str = field(default="INFO")
    log_format: str = field(default="json")
    log_file: Optional[str] = field(default=None)
    
    # File Processing
    ignore_file_patterns: List[str] = field(
        default_factory=lambda: [
            "*.min.js",
            "*.min.css",
            "*.css.map",
            "*.js.map",
            "package-lock.json",
            "yarn.lock",
            "*.png",
            "*.jpg",
            "*.jpeg",
            "*.gif",
            "*.pdf",
            "*.zip"
        ]
    )
    
    prioritize_file_patterns: List[str] = field(
        default_factory=lambda: [
            "*.py",
            "*.js",
            "*.ts",
            "*.jsx",
            "*.tsx",
            "*.java",
            "*.go",
            "*.rs",
            "*.cpp",
            "*.c",
            "*.h"
        ]
    )
    
    # Performance and Resource Management
    memory_limit_mb: int = field(default=512)
    timeout_seconds: int = field(default=300)

    # Webhook Configuration
    webhook_secret: str = field(default_factory=lambda: os.getenv("WEBHOOK_SECRET", ""))
    webhook_enabled: bool = field(default_factory=lambda: os.getenv("WEBHOOK_ENABLED", "true").lower() in ("true", "1", "yes", "on"))
    webhook_skip_draft: bool = field(default_factory=lambda: os.getenv("WEBHOOK_SKIP_DRAFT", "true").lower() in ("true", "1", "yes", "on"))
    webhook_skip_wip: bool = field(default_factory=lambda: os.getenv("WEBHOOK_SKIP_WIP", "true").lower() in ("true", "1", "yes", "on"))
    webhook_required_labels: List[str] = field(default_factory=lambda: os.getenv("WEBHOOK_REQUIRED_LABELS", "").split(",") if os.getenv("WEBHOOK_REQUIRED_LABELS") else [])
    webhook_excluded_labels: List[str] = field(default_factory=lambda: os.getenv("WEBHOOK_EXCLUDED_LABELS", "").split(",") if os.getenv("WEBHOOK_EXCLUDED_LABELS") else [])
    webhook_trigger_actions: List[str] = field(default_factory=lambda: os.getenv("WEBHOOK_TRIGGER_ACTIONS", "open,update,reopen").split(",") if os.getenv("WEBHOOK_TRIGGER_ACTIONS") else ["open", "update", "reopen"])

    # Server Configuration
    server_host: str = field(default_factory=lambda: os.getenv("SERVER_HOST", "0.0.0.0"))
    server_port: int = field(default_factory=lambda: int(os.getenv("SERVER_PORT", "8000")))
    monitoring_port: int = field(default_factory=lambda: int(os.getenv("MONITORING_PORT", "8080")))
    monitoring_host: str = field(default_factory=lambda: os.getenv("MONITORING_HOST", "0.0.0.0"))
    monitoring_enabled: bool = field(default_factory=lambda: os.getenv("MONITORING_ENABLED", "true").lower() in ("true", "1", "yes", "on"))
    enable_cors: bool = field(default_factory=lambda: os.getenv("ENABLE_CORS", "true").lower() in ("true", "1", "yes", "on"))
    cors_origins: List[str] = field(default_factory=lambda: os.getenv("CORS_ORIGINS", "*").split(",") if os.getenv("CORS_ORIGINS") else ["*"])
    max_concurrent_reviews: int = field(default_factory=lambda: int(os.getenv("MAX_CONCURRENT_REVIEWS", "3")))
    review_timeout_seconds: int = field(default_factory=lambda: int(os.getenv("REVIEW_TIMEOUT_SECONDS", "300")))

    # Deduplication Configuration
    deduplication_strategy: str = field(default_factory=lambda: os.getenv("DEDUPLICATION_STRATEGY", "content_hash"))
    deduplication_enabled: bool = field(default_factory=lambda: os.getenv("DEDUPLICATION_ENABLED", "true").lower() in ("true", "1", "yes", "on"))
    commit_tracking_ttl_hours: int = field(default_factory=lambda: int(os.getenv("COMMIT_TRACKING_TTL_HOURS", "24")))
    bot_comment_marker: str = field(default_factory=lambda: os.getenv("BOT_COMMENT_MARKER", "<!-- glm-review-bot -->"))

    def __post_init__(self):
        """Validate settings after initialization."""
        # Ensure required fields are present
        if not self.gitlab_token:
            raise ValueError("GITLAB_TOKEN environment variable is required")
        if not self.glm_api_key:
            raise ValueError("GLM_API_KEY environment variable is required")
        if not self.project_id:
            raise ValueError("CI_PROJECT_ID environment variable is required")
        if not self.mr_iid:
            raise ValueError("CI_MERGE_REQUEST_IID environment variable is required")
        
        # Validate numeric ranges
        if not 0.0 <= self.glm_temperature <= 1.0:
            raise ValueError("glm_temperature must be between 0.0 and 1.0")
        
        if self.min_severity_level not in ["low", "medium", "high"]:
            raise ValueError("min_severity_level must be one of: low, medium, high")
        
        if self.log_level not in ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]:
            raise ValueError("log_level must be one of: DEBUG, INFO, WARNING, ERROR, CRITICAL")

        # Validate webhook configuration
        if self.webhook_enabled and not self.webhook_secret:
            raise ValueError("WEBHOOK_SECRET is required when webhook_enabled is True")

        # Validate deduplication strategy
        if self.deduplication_strategy not in ["content_hash", "commit_sha", "mr_update"]:
            raise ValueError("deduplication_strategy must be one of: content_hash, commit_sha, mr_update")

        if self.commit_tracking_ttl_hours < 1:
            raise ValueError("commit_tracking_ttl_hours must be at least 1")

        # Ensure string types for API compatibility
        self.mr_iid = str(self.mr_iid)
        self.project_id = str(self.project_id)
    
    def get_gitlab_headers(self) -> Dict[str, str]:
        """Get headers for GitLab API requests."""
        return {
            "Authorization": f"Bearer {self.gitlab_token}",
            "Content-Type": "application/json"
        }
    
    def get_glm_headers(self) -> Dict[str, str]:
        """Get headers for GLM API requests."""
        return {
            "Authorization": f"Bearer {self.glm_api_key}",
            "Content-Type": "application/json"
        }
    
    def is_file_ignored(self, file_path: str) -> bool:
        """Check if a file should be ignored based on patterns."""
        import fnmatch
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_file_patterns)
    
    def is_file_prioritized(self, file_path: str) -> bool:
        """Check if a file should be prioritized based on patterns."""
        import fnmatch
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.prioritize_file_patterns)
    
    @classmethod
    def from_env(cls, **kwargs) -> "Settings":
        """Create Settings instance from environment variables with optional overrides."""
        env_vars = {}
        
        # Map environment variables to field names
        env_mapping = {
            "GITLAB_TOKEN": "gitlab_token",
            "GITLAB_API_URL": "gitlab_api_url",
            "CI_PROJECT_ID": "project_id",
            "CI_MERGE_REQUEST_IID": "mr_iid",
            "GLM_API_KEY": "glm_api_key",
            "GLM_API_URL": "glm_api_url",
            "GLM_MODEL": "glm_model",
            "GLM_TEMPERATURE": "glm_temperature",
            "GLM_MAX_TOKENS": "glm_max_tokens",
            "MAX_DIFF_SIZE": "max_diff_size",
            "MAX_FILES_PER_COMMENT": "max_files_per_comment",
            "ENABLE_INLINE_COMMENTS": "enable_inline_comments",
            "ENABLE_SECURITY_REVIEW": "enable_security_review",
            "ENABLE_PERFORMANCE_REVIEW": "enable_performance_review",
            "MIN_SEVERITY_LEVEL": "min_severity_level",
            "API_REQUEST_DELAY": "api_request_delay",
            "MAX_PARALLEL_REQUESTS": "max_parallel_requests",
            "MAX_RETRIES": "max_retries",
            "RETRY_DELAY": "retry_delay",
            "RETRY_BACKOFF_FACTOR": "retry_backoff_factor",
            "LOG_LEVEL": "log_level",
            "LOG_FORMAT": "log_format",
            "LOG_FILE": "log_file",
            "MEMORY_LIMIT_MB": "memory_limit_mb",
            "TIMEOUT_SECONDS": "timeout_seconds",
            "WEBHOOK_SECRET": "webhook_secret",
            "WEBHOOK_ENABLED": "webhook_enabled",
            "WEBHOOK_SKIP_DRAFT": "webhook_skip_draft",
            "WEBHOOK_SKIP_WIP": "webhook_skip_wip",
            "DEDUPLICATION_STRATEGY": "deduplication_strategy",
            "DEDUPLICATION_ENABLED": "deduplication_enabled",
            "COMMIT_TRACKING_TTL_HOURS": "commit_tracking_ttl_hours",
            "BOT_COMMENT_MARKER": "bot_comment_marker"
        }
        
        # Collect environment variables
        for env_var, field_name in env_mapping.items():
            if env_var in os.environ:
                env_vars[field_name] = os.environ[env_var]
        
        # Convert boolean and numeric strings
        for key, value in env_vars.items():
            if key in ["enable_inline_comments", "enable_security_review", "enable_performance_review",
                       "webhook_enabled", "webhook_skip_draft", "webhook_skip_wip", "deduplication_enabled"]:
                env_vars[key] = value.lower() in ("true", "1", "yes", "on")
            elif key in ["glm_temperature", "api_request_delay", "retry_delay", "retry_backoff_factor"]:
                env_vars[key] = float(value)
            elif key in ["glm_max_tokens", "max_diff_size", "max_files_per_comment", "max_parallel_requests",
                         "max_retries", "memory_limit_mb", "timeout_seconds", "commit_tracking_ttl_hours"]:
                env_vars[key] = int(value)
        
        # Merge with provided kwargs
        env_vars.update(kwargs)
        
        return cls(**env_vars)


# Global settings instance
class MockSettings:
    def __init__(self):
        # Diff parsing settings
        self.max_diff_size = 1000
        
        # Logging settings
        self.log_level = "INFO"
        self.log_format = "text"
        self.log_file = None
        
        # GitLab context settings for logging
        self.project_id = None
        self.mr_iid = None
        
        # GitLab client settings
        self.gitlab_token = "test_token"
        self.gitlab_api_url = "https://gitlab.example.com/api/v4"
        
        # GLM client settings
        self.glm_api_key = "test_glm_api_key"
        self.glm_api_url = "https://api.example.com/v1/chat/completions"
        
        # File filtering settings
        self.ignore_file_patterns = [
            "*.min.js", "*.min.css", "*.css.map", "*.js.map",
            "package-lock.json", "yarn.lock", "*.png", "*.jpg",
            "*.jpeg", "*.gif", "*.pdf", "*.zip"
        ]
        self.prioritize_file_patterns = [
            "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java",
            "*.go", "*.rs", "*.cpp", "*.c", "*.h"
        ]
    
    def is_file_ignored(self, file_path: str) -> bool:
        """Check if a file should be ignored based on patterns."""
        import fnmatch
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_file_patterns)
    
    def is_file_prioritized(self, file_path: str) -> bool:
        """Check if a file should be prioritized based on patterns."""
        import fnmatch
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.prioritize_file_patterns)

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
    webhook_secret: str
    webhook_enabled: bool
    webhook_skip_draft: bool
    webhook_skip_wip: bool
    webhook_required_labels: List[str]
    webhook_excluded_labels: List[str]
    webhook_trigger_actions: List[str]
    deduplication_strategy: str
    deduplication_enabled: bool
    commit_tracking_ttl_hours: int
    bot_comment_marker: str

    def is_file_ignored(self, file_path: str) -> bool: ...
    def is_file_prioritized(self, file_path: str) -> bool: ...
    def get_gitlab_headers(self) -> Dict[str, str]: ...
    def get_glm_headers(self) -> Dict[str, str]: ...


# Initialize settings from environment variables
try:
    settings = Settings.from_env()
except Exception as e:
    # Fallback to MockSettings if initialization fails
    print(f"Warning: Could not initialize Settings from environment: {e}")
    print("Using MockSettings as fallback")
    settings = MockSettings()
