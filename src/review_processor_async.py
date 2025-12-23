"""
Async Review Processor for the GLM Code Review Bot.

This module handles main async review processing logic and orchestration
for the review bot application with concurrent processing capabilities.
"""

import time
import asyncio
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .config.settings import SettingsProtocol
from .config.prompts import ReviewType
from .utils.logger import get_logger
from .utils.exceptions import ReviewBotError, CommentPublishError
from .client_manager_async import AsyncClientManager
from .chunk_processor_async import AsyncChunkProcessor


@dataclass
class ReviewContext:
    """Context information for async review process."""
    project_id: str
    mr_iid: str
    mr_details: Optional[Dict[str, Any]] = None
    diff_summary: Optional[Dict[str, Any]] = None
    processing_stats: Optional[Dict[str, Any]] = field(default_factory=dict)
    
    def update_processing_stats(self, **kwargs) -> None:
        """Update processing statistics safely."""
        if self.processing_stats is None:
            self.processing_stats = {}
        self.processing_stats.update(kwargs)


class AsyncReviewProcessor:
    """
    Handles the main async review processing logic.
    
    This class is responsible for:
    - Orchestrating the async review workflow
    - Managing async client initialization and coordination
    - Processing diff chunks with concurrent GLM analysis
    - Publishing comments with async operations
    - Handling concurrent API requests and error recovery
    """
    
    def __init__(self, settings: SettingsProtocol, concurrent_limit: int = 3):
        """
        Initialize the async review processor.
        
        Args:
            settings: Application settings instance
            concurrent_limit: Maximum number of concurrent API requests
        """
        self.settings = settings
        self.logger = get_logger("async_review_processor")
        self.concurrent_limit = concurrent_limit
        self.client_manager = AsyncClientManager(settings)
        self.chunk_processor = None
    
    async def _initialize_chunk_processor(self) -> None:
        """Initialize async chunk processor with GLM client."""
        glm_client = await self.client_manager.get_client("glm")
        self.chunk_processor = AsyncChunkProcessor(self.settings, glm_client)
    
    async def publish_comments(
        self, 
        comments: List[Any], 
        context: ReviewContext, 
        dry_run: bool = False
    ) -> None:
        """
        Async format and publish comments to GitLab.
        
        Args:
            comments: List of comments to publish
            context: Review context with MR details
            dry_run: Skip actual publication if True
            
        Raises:
            CommentPublishError: If comment publishing fails
        """
        comment_publisher = await self.client_manager.get_client("comment_publisher")
        
        try:
            self.logger.info(f"Formatting {len(comments)} comments for publication")
            
            # Create mock GLM response for comment formatting
            mock_response = {"comments": comments}
            comment_batch = comment_publisher.format_comments(mock_response)
            
            if not dry_run:
                self.logger.info("Publishing comments to GitLab")
                
                # Publish summary comment if available
                summary_comment = getattr(comment_batch, 'summary_comment', None)
                if summary_comment:
                    await comment_publisher.async_publish_review_summary(
                        summary_comment,
                        context.mr_details
                    )
                
                # Publish file comments concurrently
                file_comments = getattr(comment_batch, 'file_comments', [])
                inline_comments = getattr(comment_batch, 'inline_comments', [])
                all_file_comments = file_comments + inline_comments
                
                if all_file_comments:
                    # Publish comments concurrently with rate limiting
                    await comment_publisher.async_publish_file_comments(
                        all_file_comments,
                        context.mr_details,
                        concurrent_limit=self.concurrent_limit
                    )
                
                # Update stats
                context.update_processing_stats(
                    summary_published=summary_comment is not None,
                    file_comments_published=len(file_comments),
                    inline_comments_published=len(inline_comments)
                )
            else:
                self.logger.info(
                    "Dry run mode - skipping comment publication",
                    extra={
                        "would_publish_summary": getattr(comment_batch, 'summary_comment') is not None,
                        "would_publish_file_comments": len(getattr(comment_batch, 'file_comments', [])),
                        "would_publish_inline_comments": len(getattr(comment_batch, 'inline_comments', []))
                    }
                )
                
        except Exception as e:
            self.logger.error(f"Failed to publish comments: {e}")
            raise CommentPublishError(f"Failed to publish comments: {e}") from e
    
    async def process_merge_request(
        self,
        dry_run: bool = False,
        review_type: ReviewType = ReviewType.GENERAL,
        custom_prompt: Optional[str] = None,
        max_chunks: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Async process a single merge request end-to-end.
        
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
            project_id=getattr(self.settings, 'project_id', ''),
            mr_iid=getattr(self.settings, 'mr_iid', '')
        )
        
        try:
            self.logger.info(
                "Starting async MR review processing",
                extra={
                    "project_id": context.project_id,
                    "mr_iid": context.mr_iid,
                    "review_type": review_type.value,
                    "dry_run": dry_run,
                    "concurrent_limit": self.concurrent_limit
                }
            )
            
            # Initialize async clients
            use_real_clients = await self.client_manager.initialize_clients()
            await self._initialize_chunk_processor()
            
            if use_real_clients:
                # Process diff pipeline asynchronously
                try:
                    # Get clients
                    gitlab_client = await self.client_manager.get_client("gitlab")
                    diff_parser = await self.client_manager.get_client("diff_parser")
                    
                    # Fetch MR data concurrently
                    self.logger.info("Fetching merge request details and raw diffs concurrently")
                    mr_details_task = gitlab_client.get_merge_request_details()
                    raw_diffs_task = gitlab_client.get_merge_request_diffs_raw()

                    # Wait for both tasks to complete
                    context.mr_details, raw_diffs = await asyncio.gather(
                        mr_details_task, raw_diffs_task, return_exceptions=False
                    )

                    # Parse GitLab diff format
                    file_diffs = diff_parser.parse_gitlab_diff(raw_diffs)
                    
                    # Generate diff summary
                    if file_diffs:
                        context.diff_summary = diff_parser.get_diff_summary(file_diffs)
                    
                    # Create chunks
                    chunks = diff_parser.chunk_large_diff(file_diffs)
                    
                    if max_chunks:
                        chunks = chunks[:max_chunks]
                        self.logger.info(f"Limiting to {max_chunks} chunks")
                        
                except Exception as e:
                    self.logger.error(f"Failed to process async diff pipeline: {e}")
                    raise ReviewBotError(f"Failed to process diff pipeline: {e}") from e
                
                # Ensure chunks is a list
                if not isinstance(chunks, list):
                    chunks = []
                
                # Process chunks concurrently with GLM
                all_comments, total_tokens_used = await self.chunk_processor.process_chunks(
                    chunks, review_type, custom_prompt, self.concurrent_limit
                )
                
                # Update processing stats
                files_count = 0
                if context.diff_summary and isinstance(context.diff_summary, dict):
                    files_count = context.diff_summary.get('total_files', 0)
                
                context.update_processing_stats(
                    chunks_processed=len(chunks),
                    total_comments_generated=len(all_comments),
                    total_tokens_used=total_tokens_used,
                    files_reviewed=files_count,
                    real_clients=True,
                    concurrent_processing=True
                )
                
                # Publish comments if any were generated
                if all_comments:
                    await self.publish_comments(all_comments, context, dry_run)
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
                "Async MR review processing completed successfully",
                extra=context.processing_stats or {}
            )
            
            return {
                "status": "success",
                "message": "Async review processing completed",
                "processing_time": total_time,
                "stats": context.processing_stats,
                "context": context
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"Async MR review processing failed: {str(e)}"
            
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
    
    async def process_multiple_merge_requests(
        self,
        mr_list: List[Dict[str, str]],
        dry_run: bool = False,
        review_type: ReviewType = ReviewType.GENERAL,
        custom_prompt: Optional[str] = None,
        max_chunks: Optional[int] = None,
        concurrent_mrs: int = 2
    ) -> List[Dict[str, Any]]:
        """
        Process multiple merge requests concurrently.
        
        Args:
            mr_list: List of MR dictionaries with project_id and mr_iid
            dry_run: Skip actual comment publishing
            review_type: Type of review to perform
            custom_prompt: Custom prompt instructions
            max_chunks: Maximum number of chunks to process per MR
            concurrent_mrs: Maximum number of MRs to process concurrently
            
        Returns:
            List of processing results for each MR
        """
        if not mr_list:
            return []
        
        self.logger.info(f"Processing {len(mr_list)} MRs concurrently with limit {concurrent_mrs}")
        
        semaphore = asyncio.Semaphore(concurrent_mrs)
        
        async def process_single_mr(mr_data: Dict[str, str]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    # Update settings for this MR
                    original_project_id = getattr(self.settings, 'project_id', '')
                    original_mr_iid = getattr(self.settings, 'mr_iid', '')
                    
                    setattr(self.settings, 'project_id', mr_data.get('project_id', ''))
                    setattr(self.settings, 'mr_iid', mr_data.get('mr_iid', ''))
                    
                    result = await self.process_merge_request(
                        dry_run, review_type, custom_prompt, max_chunks
                    )
                    
                    # Restore original settings
                    setattr(self.settings, 'project_id', original_project_id)
                    setattr(self.settings, 'mr_iid', original_mr_iid)
                    
                    return {
                        "mr_data": mr_data,
                        "result": result,
                        "success": True
                    }
                    
                except Exception as e:
                    self.logger.error(f"Failed to process MR {mr_data}: {e}")
                    
                    # Restore original settings
                    setattr(self.settings, 'project_id', original_project_id)
                    setattr(self.settings, 'mr_iid', original_mr_iid)
                    
                    return {
                        "mr_data": mr_data,
                        "error": str(e),
                        "success": False
                    }
        
        try:
            results = await asyncio.gather(
                *[process_single_mr(mr) for mr in mr_list],
                return_exceptions=False
            )
            
            successful_mrs = len([r for r in results if r.get("success")])
            failed_mrs = len(mr_list) - successful_mrs
            
            self.logger.info(
                f"Concurrent MR processing completed: {successful_mrs} successful, "
                f"{failed_mrs} failed"
            )
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to process multiple MRs: {e}")
            raise ReviewBotError(f"Failed to process multiple MRs: {e}") from e


# Maintain backward compatibility
class ReviewProcessor(AsyncReviewProcessor):
    """
    Synchronous review processor for backward compatibility.
    
    This class provides the same interface as the async processor but
    executes async operations in a sync context.
    """
    
    def __init__(self, settings: SettingsProtocol, concurrent_limit: int = 3):
        super().__init__(settings, concurrent_limit)
        self.logger = get_logger("review_processor")
    
    def process_merge_request(
        self,
        dry_run: bool = False,
        review_type: ReviewType = ReviewType.GENERAL,
        custom_prompt: Optional[str] = None,
        max_chunks: Optional[int] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async method."""
        return asyncio.run(super().process_merge_request(
            dry_run, review_type, custom_prompt, max_chunks
        ))