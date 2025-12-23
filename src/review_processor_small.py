"""
Simplified Review Processor for GLM Code Review Bot.

This module handles main review processing logic with reduced complexity.
"""

import time
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from .config.settings import SettingsProtocol
from .config.prompts import ReviewType
from .utils.logger import get_logger
from .utils.exceptions import ReviewBotError, CommentPublishError


@dataclass
class ReviewContext:
    """Context information for review process."""
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


class SimpleClientManager:
    """Simplified client manager for basic functionality."""
    
    def __init__(self, settings: SettingsProtocol):
        self.settings = settings
        self.clients = {}
        self.logger = get_logger("client_manager")
    
    def initialize_clients(self) -> bool:
        """Initialize API clients."""
        try:
            from .gitlab_client import GitLabClient
            from .glm_client import GLMClient
            from .diff_parser import DiffParser
            from .comment_publisher import CommentPublisher
            
            gitlab_client = GitLabClient()
            glm_client = GLMClient(
                api_key=getattr(self.settings, 'glm_api_key', ''),
                api_url=getattr(self.settings, 'glm_api_url', ''),
                model=getattr(self.settings, 'glm_model', 'glm-4'),
                temperature=getattr(self.settings, 'glm_temperature', 0.3),
                max_tokens=getattr(self.settings, 'glm_max_tokens', 4000)
            )
            diff_parser = DiffParser(
                max_chunk_tokens=getattr(self.settings, 'max_diff_size', 50000)
            )
            comment_publisher = CommentPublisher(gitlab_client)
            
            self.clients = {
                "gitlab": gitlab_client,
                "glm": glm_client,
                "diff_parser": diff_parser,
                "comment_publisher": comment_publisher
            }
            
            self.logger.info("Successfully initialized clients")
            return True
            
        except Exception as e:
            self.logger.warning(f"Using mock clients: {e}")
            return False
    
    def get_client(self, name: str):
        """Get client by name."""
        return self.clients.get(name)


class ReviewProcessor:
    """
    Simplified review processor for main workflow orchestration.
    
    This class coordinates:
    - Client initialization
    - Diff processing pipeline
    - GLM analysis
    - Comment publishing
    """
    
    def __init__(self, settings: SettingsProtocol):
        """Initialize the review processor."""
        self.settings = settings
        self.logger = get_logger("review_processor")
        self.client_manager = SimpleClientManager(settings)
    
    def process_chunks_simple(
        self, 
        chunks: List[Any], 
        review_type: ReviewType, 
        custom_prompt: Optional[str] = None
    ) -> tuple[list[Any], int]:
        """Process chunks with GLM analysis."""
        glm_client = self.client_manager.get_client("glm")
        if not glm_client:
            return [], 0
            
        all_comments = []
        total_tokens_used = 0
        
        try:
            self.logger.info(f"Processing {len(chunks)} chunks")
            
            for i, chunk in enumerate(chunks):
                chunk_content = getattr(chunk, 'get_content', lambda: str(chunk))()
                
                glm_response = glm_client.analyze_code(
                    diff_content=chunk_content,
                    custom_prompt=custom_prompt,
                    review_type=review_type
                )
                
                if isinstance(glm_response, dict):
                    if "comments" in glm_response:
                        all_comments.extend(glm_response["comments"])
                    if "usage" in glm_response:
                        usage = glm_response["usage"]
                        if isinstance(usage, dict):
                            total_tokens_used += usage.get("total_tokens", 0)
                
                self.logger.info(f"Processed chunk {i+1}")
            
            return all_comments, total_tokens_used
            
        except Exception as e:
            self.logger.error(f"Chunk processing failed: {e}")
            raise ReviewBotError(f"Failed to process chunks: {e}") from e
    
    def publish_comments_simple(
        self, 
        comments: List[Any], 
        context: ReviewContext, 
        dry_run: bool = False
    ) -> None:
        """Format and publish comments."""
        comment_publisher = self.client_manager.get_client("comment_publisher")
        if not comment_publisher:
            return
            
        try:
            self.logger.info(f"Publishing {len(comments)} comments")
            
            if not dry_run:
                mock_response = {"comments": comments}
                comment_batch = comment_publisher.format_comments(mock_response)
                
                # Publish comments
                if hasattr(comment_batch, 'summary_comment') and comment_batch.summary_comment:
                    comment_publisher.publish_review_summary(
                        comment_batch.summary_comment,
                        context.mr_details
                    )
                
                file_comments = getattr(comment_batch, 'file_comments', [])
                inline_comments = getattr(comment_batch, 'inline_comments', [])
                all_comments = file_comments + inline_comments
                
                if all_comments:
                    comment_publisher.publish_file_comments(all_comments, context.mr_details)
                
                context.update_processing_stats(
                    summary_published=getattr(comment_batch, 'summary_comment') is not None,
                    file_comments_published=len(file_comments),
                    inline_comments_published=len(inline_comments)
                )
            else:
                self.logger.info("Dry run - skipping publication")
                
        except Exception as e:
            self.logger.error(f"Comment publishing failed: {e}")
            raise CommentPublishError(f"Failed to publish comments: {e}") from e
    
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
        """
        start_time = time.time()
        context = ReviewContext(
            project_id=getattr(self.settings, 'project_id', ''),
            mr_iid=getattr(self.settings, 'mr_iid', '')
        )
        
        try:
            self.logger.info(f"Starting MR review: {review_type.value}")
            
            # Initialize clients
            use_real_clients = self.client_manager.initialize_clients()
            
            if use_real_clients:
                # Process diff pipeline
                gitlab_client = self.client_manager.get_client("gitlab")
                diff_parser = self.client_manager.get_client("diff_parser")
                
                if not gitlab_client or not diff_parser:
                    raise ReviewBotError("Failed to initialize required clients")
                
                # Fetch MR data
                context.mr_details = gitlab_client.get_merge_request_details()
                raw_diffs = gitlab_client.get_merge_request_diffs_raw()

                # Parse diffs
                file_diffs = diff_parser.parse_gitlab_diff(raw_diffs)
                
                if file_diffs:
                    context.diff_summary = diff_parser.get_diff_summary(file_diffs)
                
                # Create chunks
                chunks = diff_parser.chunk_large_diff(file_diffs)
                if max_chunks:
                    chunks = chunks[:max_chunks]
                
                # Process chunks
                all_comments, total_tokens = self.process_chunks_simple(
                    chunks, review_type, custom_prompt
                )
                
                # Update stats
                files_count = 0
                if context.diff_summary and isinstance(context.diff_summary, dict):
                    files_count = context.diff_summary.get('total_files', 0)
                
                context.update_processing_stats(
                    chunks_processed=len(chunks),
                    total_comments_generated=len(all_comments),
                    total_tokens_used=total_tokens,
                    files_reviewed=files_count
                )
                
                # Publish comments
                if all_comments:
                    self.publish_comments_simple(all_comments, context, dry_run)
            else:
                # Mock mode
                self.logger.info("Using mock implementation")
                context.update_processing_stats(
                    chunks_processed=1, total_comments_generated=0,
                    total_tokens_used=0, files_reviewed=0
                )
            
            # Complete processing
            total_time = time.time() - start_time
            if context.processing_stats:
                context.processing_stats["total_processing_time"] = total_time
            
            return {
                "status": "success",
                "message": "Review processing completed",
                "processing_time": total_time,
                "stats": context.processing_stats,
                "context": context
            }
            
        except Exception as e:
            processing_time = time.time() - start_time
            error_msg = f"MR review processing failed: {str(e)}"
            
            self.logger.error(error_msg)
            
            if isinstance(e, ReviewBotError):
                raise
            else:
                raise ReviewBotError(error_msg) from e