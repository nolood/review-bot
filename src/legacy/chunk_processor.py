"""
Chunk Processor for the GLM Code Review Bot.

This module handles processing of diff chunks with GLM analysis.
"""

import time
from typing import List, Any, Tuple

from .config.settings import SettingsProtocol
from .config.prompts import ReviewType
from .utils.logger import get_logger
from .utils.exceptions import ReviewBotError


class ChunkProcessor:
    """
    Processes diff chunks with GLM analysis.
    
    This class is responsible for:
    - Processing individual chunks
    - Tracking token usage
    - Managing GLM client interactions
    - Collecting analysis results
    """
    
    def __init__(self, settings: SettingsProtocol, glm_client):
        """
        Initialize chunk processor.
        
        Args:
            settings: Application settings instance
            glm_client: GLM client instance
        """
        self.settings = settings
        self.glm_client = glm_client
        self.logger = get_logger("chunk_processor")
    
    def process_chunks(
        self, 
        chunks: List[Any], 
        review_type: ReviewType, 
        custom_prompt: str | None = None
    ) -> Tuple[List[Any], int]:
        """
        Process diff chunks with GLM analysis.
        
        Args:
            chunks: List of diff chunks to process
            review_type: Type of review to perform
            custom_prompt: Optional custom instructions
            
        Returns:
            Tuple of (all_comments, total_tokens_used)
            
        Raises:
            ReviewBotError: If chunk processing fails
        """
        all_comments = []
        total_tokens_used = 0
        
        try:
            self.logger.info(f"Processing {len(chunks)} chunks with {review_type.value} review")
            
            for i, chunk in enumerate(chunks):
                self.logger.info(f"Processing chunk {i+1}/{len(chunks)}")
                
                chunk_start_time = time.time()
                chunk_content = getattr(chunk, 'get_content', lambda: str(chunk))()
                
                # Analyze with GLM
                glm_response = self.glm_client.analyze_code(
                    diff_content=chunk_content,
                    custom_prompt=custom_prompt,
                    review_type=review_type
                )
                
                # Extract and store comments
                if isinstance(glm_response, dict) and "comments" in glm_response:
                    all_comments.extend(glm_response["comments"])
                
                # Track token usage
                if isinstance(glm_response, dict) and "usage" in glm_response:
                    usage = glm_response["usage"]
                    if isinstance(usage, dict):
                        total_tokens_used += usage.get("total_tokens", 0)
                
                chunk_time = time.time() - chunk_start_time
                self.logger.info(
                    f"Chunk {i+1} processed in {chunk_time:.2f}s",
                    extra={
                        "chunk_number": i+1,
                        "chunk_files": len(getattr(chunk, 'files', [])),
                        "chunk_tokens": getattr(chunk, 'estimated_tokens', 0),
                        "processing_time": chunk_time
                    }
                )
            
            return all_comments, total_tokens_used
            
        except Exception as e:
            self.logger.error(f"Failed to process chunks: {e}")
            raise ReviewBotError(f"Failed to process chunks: {e}") from e
    
    def estimate_processing_time(self, chunks: List[Any]) -> float:
        """
        Estimate processing time for chunks.
        
        Args:
            chunks: List of chunks to process
            
        Returns:
            Estimated processing time in seconds
        """
        try:
            total_files = sum(len(getattr(chunk, 'files', [])) for chunk in chunks)
            total_tokens = sum(getattr(chunk, 'estimated_tokens', 1000) for chunk in chunks)
            
            # Rough estimation: 1 second per chunk + 0.1 seconds per 1000 tokens
            estimated_time = len(chunks) + (total_tokens / 1000) * 0.1
            
            return estimated_time
            
        except Exception as e:
            self.logger.warning(f"Failed to estimate processing time: {e}")
            return len(chunks) * 2.0  # Fallback estimate
    
    def get_chunk_statistics(self, chunks: List[Any]) -> dict[str, Any]:
        """
        Get statistics about chunks.
        
        Args:
            chunks: List of chunks
            
        Returns:
            Dictionary with chunk statistics
        """
        try:
            stats = {
                "total_chunks": len(chunks),
                "total_files": 0,
                "total_estimated_tokens": 0,
                "average_files_per_chunk": 0,
                "average_tokens_per_chunk": 0
            }
            
            if chunks:
                for chunk in chunks:
                    chunk_files = len(getattr(chunk, 'files', []))
                    chunk_tokens = getattr(chunk, 'estimated_tokens', 0)
                    
                    stats["total_files"] += chunk_files
                    stats["total_estimated_tokens"] += chunk_tokens
                
                stats["average_files_per_chunk"] = stats["total_files"] / len(chunks)  # type: ignore
                stats["average_tokens_per_chunk"] = stats["total_estimated_tokens"] / len(chunks)  # type: ignore
            
            return stats
            
        except Exception as e:
            self.logger.warning(f"Failed to get chunk statistics: {e}")
            return {"total_chunks": len(chunks)}