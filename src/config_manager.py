"""
Configuration Manager for the GLM Code Review Bot.

This module handles configuration management and environment validation
for the review bot application.
"""

import os
import fnmatch
from typing import Dict, List, Optional

from .config.settings import SettingsProtocol
from .utils.logger import get_logger
from .utils.exceptions import ConfigurationError


class ConfigurationManager:
    """
    Manages application configuration and environment validation.
    
    This class is responsible for:
    - Loading and validating configuration
    - Environment variable validation
    - URL and parameter validation
    - File pattern management
    """
    
    # Application constants
    GLM_API_URL_DEFAULT = "https://api.z.ai/api/paas/v4/chat/completions"
    GITLAB_API_URL_DEFAULT = "https://gitlab.com/api/v4"
    
    # Required environment variables
    REQUIRED_VARS_DRY_RUN = ["GLM_API_KEY"]
    REQUIRED_VARS_FULL = ["GLM_API_KEY", "GITLAB_TOKEN", "CI_PROJECT_ID", "CI_MERGE_REQUEST_IID"]
    
    def __init__(self, settings: SettingsProtocol):
        """
        Initialize the configuration manager.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.logger = get_logger("config")
    
    def validate_url(self, url: str, name: str) -> None:
        """
        Validate that a URL has proper format.
        
        Args:
            url: URL to validate
            name: Name of the URL parameter for error messages
            
        Raises:
            ConfigurationError: If URL format is invalid
        """
        if not url.startswith(("http://", "https://")):
            raise ConfigurationError(f"Invalid {name}: {url}")
    
    def validate_range(self, value: float, min_val: float, max_val: float, name: str) -> None:
        """
        Validate that a numeric value is within range.
        
        Args:
            value: Value to validate
            min_val: Minimum allowed value
            max_val: Maximum allowed value
            name: Name of the parameter for error messages
            
        Raises:
            ConfigurationError: If value is out of range
        """
        if not min_val <= value <= max_val:
            raise ConfigurationError(
                f"Invalid {name}: {value}. Must be between {min_val} and {max_val}"
            )
    
    def validate_positive(self, value: int, name: str) -> None:
        """
        Validate that a numeric value is positive.
        
        Args:
            value: Value to validate
            name: Name of the parameter for error messages
            
        Raises:
            ConfigurationError: If value is not positive
        """
        if value <= 0:
            raise ConfigurationError(
                f"Invalid {name}: {value}. Must be positive"
            )
    
    def get_env_value(self, var_name: str) -> str:
        """
        Get environment value from settings or environment.
        
        Args:
            var_name: Environment variable name
            
        Returns:
            Environment variable value
        """
        env_mapping = {
            "GLM_API_KEY": "glm_api_key",
            "GITLAB_TOKEN": "gitlab_token",
            "CI_PROJECT_ID": "project_id",
            "CI_MERGE_REQUEST_IID": "mr_iid"
        }
        
        if var_name in env_mapping and hasattr(self.settings, env_mapping[var_name]):
            return getattr(self.settings, env_mapping[var_name])
        return os.getenv(var_name, "")
    
    def validate_environment(self, dry_run: bool = False) -> bool:
        """
        Validate all required environment variables and settings.
        
        Args:
            dry_run: Whether this is a dry run (relaxes some requirements)
            
        Returns:
            True if validation passes
            
        Raises:
            ConfigurationError: If required settings are missing or invalid
        """
        self.logger.info("Validating environment and configuration")
        
        try:
            # Determine required variables based on run mode
            required_vars = self.REQUIRED_VARS_DRY_RUN.copy()
            if not dry_run:
                required_vars.extend(self.REQUIRED_VARS_FULL[1:])  # Skip GLM_API_KEY as it's already included
            
            # Check for missing variables
            missing_vars = []
            for var in required_vars:
                env_value = self.get_env_value(var)
                if not env_value:
                    missing_vars.append(var)
            
            if missing_vars:
                raise ConfigurationError(
                    f"Missing required environment variables: {', '.join(missing_vars)}"
                )
            
            # Validate temperature range
            if hasattr(self.settings, 'glm_temperature'):
                self.validate_range(
                    self.settings.glm_temperature, 0.0, 1.0, "GLM temperature"
                )
            
            # Validate positive values
            if hasattr(self.settings, 'max_diff_size'):
                self.validate_positive(self.settings.max_diff_size, "max_diff_size")
            
            # Validate file patterns
            if hasattr(self.settings, 'ignore_file_patterns') and not self.settings.ignore_file_patterns:
                self.logger.warning("No ignore file patterns configured")
            
            if hasattr(self.settings, 'prioritize_file_patterns') and not self.settings.prioritize_file_patterns:
                self.logger.warning("No prioritize file patterns configured")
            
            # Validate API URLs
            if hasattr(self.settings, 'gitlab_api_url'):
                self.validate_url(self.settings.gitlab_api_url, "GitLab API URL")
            
            if hasattr(self.settings, 'glm_api_url'):
                self.validate_url(self.settings.glm_api_url, "GLM API URL")
            
            self.logger.info("Environment validation completed successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Environment validation failed: {e}")
            raise ConfigurationError(f"Environment validation failed: {e}") from e
    
    def is_file_ignored(self, file_path: str) -> bool:
        """
        Check if a file should be ignored based on patterns.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file should be ignored, False otherwise
        """
        if hasattr(self.settings, 'is_file_ignored'):
            return self.settings.is_file_ignored(file_path)
        
        # Fallback implementation
        if hasattr(self.settings, 'ignore_file_patterns'):
            return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.settings.ignore_file_patterns)
        return False
    
    def is_file_prioritized(self, file_path: str) -> bool:
        """
        Check if a file should be prioritized based on patterns.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            True if file should be prioritized, False otherwise
        """
        if hasattr(self.settings, 'is_file_prioritized'):
            return self.settings.is_file_prioritized(file_path)
        
        # Fallback implementation
        if hasattr(self.settings, 'prioritize_file_patterns'):
            return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.settings.prioritize_file_patterns)
        return False
    
    def get_gitlab_headers(self) -> Dict[str, str]:
        """
        Get headers for GitLab API requests.
        
        Returns:
            Dictionary of HTTP headers for GitLab API
        """
        if hasattr(self.settings, 'get_gitlab_headers'):
            return self.settings.get_gitlab_headers()
        
        # Fallback implementation
        return {
            "Authorization": f"Bearer {getattr(self.settings, 'gitlab_token', '')}",
            "Content-Type": "application/json"
        }
    
    def get_glm_headers(self) -> Dict[str, str]:
        """
        Get headers for GLM API requests.
        
        Returns:
            Dictionary of HTTP headers for GLM API
        """
        if hasattr(self.settings, 'get_glm_headers'):
            return self.settings.get_glm_headers()
        
        # Fallback implementation
        return {
            "Authorization": f"Bearer {getattr(self.settings, 'glm_api_key', '')}",
            "Content-Type": "application/json"
        }
    
    def get_setting(self, key: str, default=None):
        """
        Get a setting value by key with fallback.
        
        Args:
            key: Setting key to retrieve
            default: Default value if key not found
            
        Returns:
            Setting value or default
        """
        return getattr(self.settings, key, default)
    
    def validate_setting(self, key: str, validator_func, error_message: Optional[str] = None) -> None:
        """
        Validate a specific setting using a validator function.
        
        Args:
            key: Setting key to validate
            validator_func: Function that takes the value and returns True if valid
            error_message: Custom error message
            
        Raises:
            ConfigurationError: If validation fails
        """
        if hasattr(self.settings, key):
            value = getattr(self.settings, key)
            if not validator_func(value):
                msg = error_message or f"Invalid {key}: {value}"
                raise ConfigurationError(msg)