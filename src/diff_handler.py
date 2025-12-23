"""
Diff Handler for the GLM Code Review Bot.

This module handles diff processing coordination and chunking logic
for the review bot application.
"""

import time
from typing import List, Dict, Any, Optional, Tuple

from .config.settings import SettingsProtocol
from .config.prompts import ReviewType
from .utils.logger import get_logger
from .utils.exceptions import ReviewBotError, DiffParsingError


class DiffHandler:
    """
    Handles diff processing and chunking operations.
    
    This class is responsible for:
    - Coordinating diff fetching and parsing
    - Managing chunk creation and processing
    - Tracking diff statistics and metadata
    - Handling large diff processing strategies
    """
    
    def __init__(self, settings: SettingsProtocol, diff_parser, gitlab_client):
        """
        Initialize the diff handler.
        
        Args:
            settings: Application settings instance
            diff_parser: Diff parser instance
            gitlab_client: GitLab client instance
        """
        self.settings = settings
        self.diff_parser = diff_parser
        self.gitlab_client = gitlab_client
        self.logger = get_logger("diff_handler")
    
    def fetch_merge_request_data(self) -> Tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """
        Fetch merge request details and raw diff data.

        Returns:
            Tuple of (mr_details, raw_diffs)

        Raises:
            ReviewBotError: If fetching fails
        """
        try:
            # Fetch MR details
            self.logger.info("Fetching merge request details")
            mr_details = self.gitlab_client.get_merge_request_details()

            # Fetch raw diff data from GitLab API
            self.logger.info("Fetching raw merge request diffs")
            raw_diffs = self.gitlab_client.get_merge_request_diffs_raw()

            return mr_details, raw_diffs

        except Exception as e:
            self.logger.error(f"Failed to fetch merge request data: {e}")
            raise ReviewBotError(f"Failed to fetch merge request data: {e}") from e
    
    def parse_diff_data(self, raw_diffs: List[Dict[str, Any]]) -> Tuple[List[Any], Dict[str, Any]]:
        """
        Parse raw GitLab diff data into structured format.

        Args:
            raw_diffs: Raw diff objects from GitLab API

        Returns:
            Tuple of (file_diffs, diff_summary)

        Raises:
            DiffParsingError: If parsing fails
        """
        try:
            # Parse GitLab diff format directly
            self.logger.info(f"Parsing {len(raw_diffs)} GitLab diff entries")
            file_diffs = self.diff_parser.parse_gitlab_diff(raw_diffs)

            # Generate diff summary
            diff_summary = {}
            if file_diffs:
                diff_summary = self.diff_parser.get_diff_summary(file_diffs)
                self.logger.info("Diff parsing completed", extra=diff_summary)
            else:
                self.logger.warning("No file diffs parsed from GitLab data")

            return file_diffs, diff_summary

        except Exception as e:
            self.logger.error(f"Failed to parse diff data: {e}")
            raise DiffParsingError(f"Failed to parse diff data: {e}") from e
    
    def create_chunks(self, file_diffs: List[Any], max_chunks: Optional[int] = None) -> List[Any]:
        """
        Create chunks from file diffs for processing.
        
        Args:
            file_diffs: List of parsed file diffs
            max_chunks: Maximum number of chunks to create
            
        Returns:
            List of diff chunks
        """
        try:
            self.logger.info(f"Creating diff chunks from {len(file_diffs)} files")
            
            # Create chunks using diff parser
            chunks = self.diff_parser.chunk_large_diff(file_diffs)
            
            # Apply chunk limit if specified
            if max_chunks:
                original_count = len(chunks)
                chunks = chunks[:max_chunks]
                self.logger.info(f"Limited chunks from {original_count} to {max_chunks}")
            
            self.logger.info(f"Created {len(chunks)} chunks for processing")
            return chunks
            
        except Exception as e:
            self.logger.error(f"Failed to create chunks: {e}")
            raise ReviewBotError(f"Failed to create chunks: {e}") from e
    
    def filter_files(self, file_diffs: List[Any]) -> List[Any]:
        """
        Filter files based on ignore and prioritize patterns.
        
        Args:
            file_diffs: List of file diffs to filter
            
        Returns:
            Filtered list of file diffs
        """
        try:
            filtered_files = []
            ignored_count = 0
            
            for file_diff in file_diffs:
                file_path = getattr(file_diff, 'file_path', '') or getattr(file_diff, 'new_path', '')
                
                if not file_path:
                    # If no file path, include it (shouldn't happen but be safe)
                    filtered_files.append(file_diff)
                    continue
                
                # Check if file should be ignored
                if hasattr(self.settings, 'is_file_ignored') and self.settings.is_file_ignored(file_path):
                    ignored_count += 1
                    continue
                
                filtered_files.append(file_diff)
            
            if ignored_count > 0:
                self.logger.info(f"Ignored {ignored_count} files based on patterns")
            
            return filtered_files
            
        except Exception as e:
            self.logger.error(f"Failed to filter files: {e}")
            # Return original list if filtering fails
            return file_diffs
    
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
    
    def get_chunk_statistics(self, chunks: List[Any]) -> Dict[str, Any]:
        """
        Get statistics about the chunks.
        
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
    
    def process_diff_pipeline(
        self, 
        max_chunks: Optional[int] = None
    ) -> Tuple[List[Any], Dict[str, Any], Dict[str, Any]]:
        """
        Run the complete diff processing pipeline.
        
        Args:
            max_chunks: Maximum number of chunks to process
            
        Returns:
            Tuple of (chunks, mr_details, diff_summary)
            
        Raises:
            ReviewBotError: If pipeline fails
        """
        start_time = time.time()
        
        try:
            # Fetch data
            mr_details, diff_data = self.fetch_merge_request_data()
            
            # Parse diff
            file_diffs, diff_summary = self.parse_diff_data(diff_data)
            
            # Filter files
            filtered_files = self.filter_files(file_diffs)
            
            if not filtered_files:
                self.logger.warning("No files to review after filtering")
                return [], mr_details, diff_summary
            
            # Create chunks
            chunks = self.create_chunks(filtered_files, max_chunks)
            
            # Log pipeline statistics
            pipeline_time = time.time() - start_time
            chunk_stats = self.get_chunk_statistics(chunks)
            estimated_time = self.estimate_processing_time(chunks)
            
            self.logger.info(
                "Diff processing pipeline completed",
                extra={
                    "pipeline_time": pipeline_time,
                    "total_files_found": len(file_diffs),
                    "files_after_filtering": len(filtered_files),
                    "chunks_created": len(chunks),
                    "estimated_processing_time": estimated_time,
                    **chunk_stats
                }
            )
            
            return chunks, mr_details, diff_summary
            
        except Exception as e:
            pipeline_time = time.time() - start_time
            self.logger.error(
                f"Diff processing pipeline failed after {pipeline_time:.2f}s: {e}"
            )
            raise ReviewBotError(f"Diff processing pipeline failed: {e}") from e
    
    def validate_diff_size(self, diff_summary: Dict[str, Any]) -> bool:
        """
        Validate that diff size is within acceptable limits.
        
        Args:
            diff_summary: Diff summary statistics
            
        Returns:
            True if diff size is acceptable, False otherwise
        """
        try:
            max_diff_size = getattr(self.settings, 'max_diff_size', 50000)
            total_lines = diff_summary.get('total_lines', 0)
            estimated_tokens = diff_summary.get('estimated_tokens', 0)
            
            if total_lines > max_diff_size:
                self.logger.warning(
                    f"Diff size ({total_lines} lines) exceeds limit ({max_diff_size})"
                )
                return False
            
            if estimated_tokens > max_diff_size:
                self.logger.warning(
                    f"Estimated tokens ({estimated_tokens}) exceed limit ({max_diff_size})"
                )
                return False
            
            return True
            
        except Exception as e:
            self.logger.warning(f"Failed to validate diff size: {e}")
            return True  # Assume valid if validation fails