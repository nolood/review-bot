"""
Client Manager for the GLM Code Review Bot.

This module handles initialization and management of API clients.
"""

from typing import Dict, Any

from .config.settings import SettingsProtocol
from .utils.logger import get_logger
from .utils.exceptions import ReviewBotError


class ClientManager:
    """
    Manages API client initialization and coordination.
    
    This class is responsible for:
    - Initializing all required API clients
    - Providing mock fallbacks when imports fail
    - Managing client lifecycle
    """
    
    def __init__(self, settings: SettingsProtocol):
        """
        Initialize client manager.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.logger = get_logger("client_manager")
        self.clients = {}
    
    def initialize_clients(self) -> bool:
        """
        Initialize API clients.
        
        Returns:
            True if real clients were initialized, False if using mock clients
            
        Raises:
            ReviewBotError: If client initialization fails critically
        """
        try:
            # Import here to avoid circular dependencies
            from .gitlab_client import GitLabClient
            from .glm_client import GLMClient
            from .diff_parser import DiffParser
            from .comment_publisher import CommentPublisher
            
            # Initialize GitLab client
            gitlab_client = GitLabClient()
            
            # Initialize GLM client
            glm_client = GLMClient(
                api_key=getattr(self.settings, 'glm_api_key', ''),
                api_url=getattr(self.settings, 'glm_api_url', ''),
                model=getattr(self.settings, 'glm_model', 'glm-4'),
                temperature=getattr(self.settings, 'glm_temperature', 0.3),
                max_tokens=getattr(self.settings, 'glm_max_tokens', 4000)
            )
            
            # Initialize diff parser
            diff_parser = DiffParser(
                max_chunk_tokens=getattr(self.settings, 'max_diff_size', 50000)
            )
            
            # Initialize comment publisher
            comment_publisher = CommentPublisher(gitlab_client)
            
            self.clients = {
                "gitlab": gitlab_client,
                "glm": glm_client,
                "diff_parser": diff_parser,
                "comment_publisher": comment_publisher
            }
            
            self.logger.info("Successfully initialized all API clients")
            return True
            
        except ImportError as e:
            self.logger.warning(f"Could not import real clients: {e}, using mock implementation")
            self._initialize_mock_clients()
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize clients: {e}")
            raise ReviewBotError(f"Failed to initialize clients: {e}") from e
    
    def _initialize_mock_clients(self) -> None:
        """Initialize mock clients for testing/fallback scenarios."""
        class MockClient:
            def __getattr__(self, name):
                def mock_method(*args, **kwargs):
                    return {}
                return mock_method
        
        self.clients = {
            "gitlab": MockClient(),
            "glm": MockClient(),
            "diff_parser": MockClient(),
            "comment_publisher": MockClient()
        }
    
    def get_client(self, client_name: str):
        """
        Get a specific client by name.
        
        Args:
            client_name: Name of the client to retrieve
            
        Returns:
            Client instance or None if not found
        """
        return self.clients.get(client_name)
    
    def get_all_clients(self) -> Dict[str, Any]:
        """
        Get all clients.
        
        Returns:
            Dictionary of all clients
        """
        return self.clients.copy()