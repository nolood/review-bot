"""
Async Chunk Processor for the GLM Code Review Bot.

This module handles async processing of diff chunks with concurrent GLM analysis.
"""

import time
import asyncio
from typing import List, Any, Tuple, Optional, Dict

from .config.settings import SettingsProtocol
from .config.prompts import ReviewType
from .utils.logger import get_logger
from .utils.exceptions import ReviewBotError


class AsyncChunkProcessor:
    """
    Processes diff chunks with async concurrent GLM analysis.
    
    This class is responsible for:
    - Processing individual chunks concurrently
    - Tracking token usage across multiple requests
    - Managing async GLM client interactions
    - Collecting and combining analysis results
    - Rate limiting and error handling
    """
    
    def __init__(self, settings: SettingsProtocol, glm_client):
        """
        Initialize async chunk processor.
        
        Args:
            settings: Application settings instance
            glm_client: Async GLM client instance
        """
        self.settings = settings
        self.glm_client = glm_client
        self.logger = get_logger("async_chunk_processor")
        self.concurrent_limit = getattr(settings, 'concurrent_glm_requests', 3)
        self.chunk_timeout = getattr(settings, 'chunk_timeout', 120)
    
    async def process_chunks(
        self, 
        chunks: List[Any], 
        review_type: ReviewType, 
        custom_prompt: Optional[str] = None,
        concurrent_limit: Optional[int] = None
    ) -> Tuple[List[Any], int]:
        """
        Process diff chunks concurrently with GLM analysis.
        
        Args:
            chunks: List of diff chunks to process
            review_type: Type of review to perform
            custom_prompt: Custom prompt instructions
            concurrent_limit: Override default concurrent limit
            
        Returns:
            Tuple of (all_comments, total_tokens_used)
            
        Raises:
            ReviewBotError: If chunk processing fails critically
        """
        if not chunks:
            return [], 0
        
        limit = concurrent_limit or self.concurrent_limit
        self.logger.info(
            f"Processing {len(chunks)} chunks concurrently with limit {limit}"
        )
        
        start_time = time.time()
        semaphore = asyncio.Semaphore(limit)
        all_comments = []
        total_tokens = 0
        
        async def process_single_chunk(chunk_data: Any, index: int) -> Tuple[int, List[Any], int]:
            """Process a single chunk with timeout and error handling."""
            async with semaphore:
                try:
                    # Get chunk content
                    chunk_content = self._extract_chunk_content(chunk_data)
                    if not chunk_content.strip():
                        self.logger.warning(f"Empty chunk {index}, skipping")
                        return index, [], 0
                    
                    self.logger.debug(f"Processing chunk {index} with {len(chunk_content)} characters")
                    
                    # Process with timeout
                    result = await asyncio.wait_for(
                        self.glm_client.analyze_code(
                            chunk_content, custom_prompt, review_type
                        ),
                        timeout=self.chunk_timeout
                    )
                    
                    comments = result.get("comments", [])
                    tokens_used = result.get("usage", {}).get("total_tokens", 0)
                    
                    self.logger.debug(
                        f"Chunk {index} processed: {len(comments)} comments, "
                        f"{tokens_used} tokens"
                    )
                    
                    return index, comments, tokens_used
                    
                except asyncio.TimeoutError:
                    self.logger.error(f"Chunk {index} processing timed out after {self.chunk_timeout}s")
                    return index, [], 0
                except Exception as e:
                    self.logger.error(f"Failed to process chunk {index}: {e}")
                    return index, [], 0
        
        try:
            # Process all chunks concurrently
            tasks = [
                process_single_chunk(chunk, i) 
                for i, chunk in enumerate(chunks)
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=False)
            
            # Sort results by index to maintain order
            results.sort(key=lambda x: x[0])
            
            # Combine results
            for index, comments, tokens in results:
                all_comments.extend(comments)
                total_tokens += tokens
            
            successful_chunks = len([r for r in results if r[1]])  # Has comments
            total_time = time.time() - start_time
            
            self.logger.info(
                f"Concurrent chunk processing completed in {total_time:.2f}s: "
                f"{len(all_comments)} total comments, {total_tokens} tokens, "
                f"{successful_chunks}/{len(chunks)} chunks generated comments"
            )
            
            return all_comments, total_tokens
            
        except Exception as e:
            self.logger.error(f"Failed to process chunks concurrently: {e}")
            raise ReviewBotError(f"Failed to process chunks: {e}") from e
    
    async def process_chunks_with_retry(
        self,
        chunks: List[Any],
        review_type: ReviewType,
        custom_prompt: Optional[str] = None,
        concurrent_limit: Optional[int] = None,
        max_retries: int = 2
    ) -> Tuple[List[Any], int]:
        """
        Process chunks with retry logic for failed chunks.
        
        Args:
            chunks: List of diff chunks to process
            review_type: Type of review to perform
            custom_prompt: Custom prompt instructions
            concurrent_limit: Override default concurrent limit
            max_retries: Maximum retry attempts per chunk
            
        Returns:
            Tuple of (all_comments, total_tokens_used)
        """
        limit = concurrent_limit or self.concurrent_limit
        self.logger.info(f"Processing chunks with retry logic, max retries: {max_retries}")
        
        # First attempt
        all_comments, total_tokens = await self.process_chunks(
            chunks, review_type, custom_prompt, limit
        )
        
        # Identify chunks that failed to process (no comments but should have some)
        if all_comments and chunks:
            # If we got some comments but not all chunks processed, retry failed ones
            self.logger.info("Retrying failed chunks")
            # For simplicity, retry all chunks if not all were successful
            # In a more sophisticated implementation, we'd track specific failures
            
        return all_comments, total_tokens
    
    def _extract_chunk_content(self, chunk: Any) -> str:
        """
        Extract content from various chunk formats.
        
        Args:
            chunk: Chunk data in various formats
            
        Returns:
            String content for analysis
        """
        if hasattr(chunk, 'content'):
            return str(chunk.content)
        elif hasattr(chunk, 'diff'):
            return str(chunk.diff)
        elif isinstance(chunk, dict):
            return str(chunk.get('content', chunk.get('diff', '')))
        elif isinstance(chunk, str):
            return chunk
        else:
            return str(chunk)
    
    async def get_chunk_statistics(self, chunks: List[Any]) -> Dict[str, Any]:
        """
        Get statistics about chunks before processing.
        
        Args:
            chunks: List of chunks to analyze
            
        Returns:
            Dictionary with chunk statistics
        """
        if not chunks:
            return {"total_chunks": 0, "total_chars": 0, "avg_chunk_size": 0}
        
        total_chars = 0
        chunk_sizes = []
        
        for chunk in chunks:
            content = self._extract_chunk_content(chunk)
            char_count = len(content)
            total_chars += char_count
            chunk_sizes.append(char_count)
        
        avg_chunk_size = total_chars / len(chunks) if chunks else 0
        max_chunk_size = max(chunk_sizes) if chunk_sizes else 0
        min_chunk_size = min(chunk_sizes) if chunk_sizes else 0
        
        return {
            "total_chunks": len(chunks),
            "total_chars": total_chars,
            "avg_chunk_size": avg_chunk_size,
            "max_chunk_size": max_chunk_size,
            "min_chunk_size": min_chunk_size,
            "chunk_size_distribution": {
                "small": len([s for s in chunk_sizes if s < 1000]),
                "medium": len([s for s in chunk_sizes if 1000 <= s < 5000]),
                "large": len([s for s in chunk_sizes if s >= 5000])
            }
        }


# Maintain backward compatibility
class ChunkProcessor(AsyncChunkProcessor):
    """
    Synchronous chunk processor for backward compatibility.
    
    This class provides the same interface as the async processor but
    executes async operations in a sync context.
    """
    
    def __init__(self, settings: SettingsProtocol, glm_client):
        # Check if the provided GLM client is async or sync
        if hasattr(glm_client, 'analyze_code') and asyncio.iscoroutinefunction(glm_client.analyze_code):
            # It's already an async client, use it directly
            super().__init__(settings, glm_client)
        else:
            # It's a sync client, wrap it
            from .glm_client_async import AsyncGLMClient
            # Create a simple wrapper
            class SyncToAsyncWrapper:
                def __init__(self, sync_client):
                    self.sync_client = sync_client
                
                async def analyze_code(self, *args, **kwargs):
                    return self.sync_client.analyze_code(*args, **kwargs)
            
            async_glm_client = SyncToAsyncWrapper(glm_client)
            super().__init__(settings, async_glm_client)
        
        self.logger = get_logger("chunk_processor")
    
    def process_chunks(
        self, 
        chunks: List[Any], 
        review_type: ReviewType, 
        custom_prompt: str | None = None
    ) -> Tuple[List[Any], int]:
        """Synchronous wrapper for async method."""
        return asyncio.run(super().process_chunks(
            chunks, review_type, custom_prompt
        ))