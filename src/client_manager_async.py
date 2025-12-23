"""
Async Client Manager for the GLM Code Review Bot.

This module handles async initialization and management of API clients
with concurrent processing capabilities.
"""

from typing import Dict, Any
import asyncio

from .config.settings import SettingsProtocol
from .utils.logger import get_logger
from .utils.exceptions import ReviewBotError


class AsyncClientManager:
    """
    Manages async API client initialization and coordination.
    
    This class is responsible for:
    - Initializing all required async API clients
    - Providing mock fallbacks when imports fail
    - Managing async client lifecycle
    - Supporting concurrent client operations
    """
    
    def __init__(self, settings: SettingsProtocol):
        """
        Initialize async client manager.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.logger = get_logger("async_client_manager")
        self.clients = {}
    
    async def initialize_clients(self) -> bool:
        """
        Initialize async API clients.
        
        Returns:
            True if real clients were initialized, False if using mock clients
            
        Raises:
            ReviewBotError: If client initialization fails critically
        """
        try:
            # Import here to avoid circular dependencies
            from .gitlab_client_async import AsyncGitLabClient
            from .glm_client_async import AsyncGLMClient
            from .diff_parser import DiffParser
            from .comment_publisher import CommentPublisher
            
            # Initialize async GitLab client
            gitlab_client = AsyncGitLabClient(
                timeout=getattr(self.settings, 'gitlab_timeout', 60),
                limits=getattr(self.settings, 'http_limits', None)
            )
            
            # Initialize async GLM client
            glm_client = AsyncGLMClient(
                api_key=getattr(self.settings, 'glm_api_key', ''),
                api_url=getattr(self.settings, 'glm_api_url', ''),
                model=getattr(self.settings, 'glm_model', 'glm-4'),
                temperature=getattr(self.settings, 'glm_temperature', 0.3),
                max_tokens=getattr(self.settings, 'glm_max_tokens', 4000),
                timeout=getattr(self.settings, 'glm_timeout', 60),
                limits=getattr(self.settings, 'http_limits', None)
            )
            
            # Initialize diff parser (synchronous)
            diff_parser = DiffParser(
                max_chunk_tokens=getattr(self.settings, 'max_diff_size', 50000)
            )
            
            # Initialize comment publisher (synchronous)
            comment_publisher = CommentPublisher(gitlab_client)
            
            self.clients = {
                "gitlab": gitlab_client,
                "glm": glm_client,
                "diff_parser": diff_parser,
                "comment_publisher": comment_publisher
            }
            
            self.logger.info("Successfully initialized all async API clients")
            return True
            
        except ImportError as e:
            self.logger.warning(f"Could not import real async clients: {e}, using mock implementation")
            await self._initialize_mock_clients()
            return False
        except Exception as e:
            self.logger.error(f"Failed to initialize async clients: {e}")
            raise ReviewBotError(f"Failed to initialize async clients: {e}") from e
    
    async def _initialize_mock_clients(self) -> None:
        """Initialize mock clients for testing/fallback scenarios."""
        class MockAsyncClient:
            async def __getattr__(self, name):
                async def mock_async_method(*args, **kwargs):
                    return {}
                return mock_async_method
        
        class MockSyncClient:
            def __getattr__(self, name):
                def mock_sync_method(*args, **kwargs):
                    return {}
                return mock_sync_method
        
        self.clients = {
            "gitlab": MockAsyncClient(),
            "glm": MockAsyncClient(),
            "diff_parser": MockSyncClient(),
            "comment_publisher": MockSyncClient()
        }
    
    async def get_client(self, client_name: str):
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
    
    async def close_all_clients(self) -> None:
        """Close all async clients and cleanup resources."""
        try:
            for client_name, client in self.clients.items():
                if hasattr(client, 'aclose'):
                    await client.aclose()
                elif hasattr(client, '_client') and hasattr(client._client, 'aclose'):
                    await client._client.aclose()
                elif hasattr(client, '_async_client') and hasattr(client._async_client, '_client'):
                    if hasattr(client._async_client._client, 'aclose'):
                        await client._async_client._client.aclose()
            
            self.logger.info("Successfully closed all async clients")
        except Exception as e:
            self.logger.error(f"Error closing async clients: {e}")
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize_clients()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close_all_clients()


# Maintain backward compatibility
class ClientManager(AsyncClientManager):
    """
    Synchronous client manager for backward compatibility.
    
    This class provides the same interface as the async manager but
    executes async operations in a sync context.
    """
    
    def initialize_clients(self) -> bool:
        """Synchronous wrapper for async method."""
        return asyncio.run(super().initialize_clients())
    
    def get_client(self, client_name: str):
        """Synchronous wrapper for async method - returns client directly."""
        # In sync mode, we need to handle the async client differently
        return self.clients.get(client_name)
    
    def close_all_clients(self):
        """Synchronous wrapper for async method."""
        return asyncio.run(super().close_all_clients())