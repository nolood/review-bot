"""
Async CLI Handler for GLM Code Review Bot.

This module handles async command-line argument parsing and validation
for the async review bot application with concurrent processing options.
"""

import argparse
import sys
import asyncio
from typing import Optional, List

from .config.prompts import ReviewType
from .utils.logger import get_logger, setup_logging
from .utils.exceptions import ReviewBotError, ConfigurationError


class AsyncCLIHandler:
    """
    Handles async command-line interface and execution for review bot.
    
    This class is responsible for:
    - Parsing and validating command-line arguments
    - Setting up logging configuration
    - Providing async execution options
    - Managing concurrent processing parameters
    """
    
    def __init__(self, settings):
        """
        Initialize async CLI handler with settings.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.logger = None
    
    def create_parser(self) -> argparse.ArgumentParser:
        """
        Create and configure argument parser with async options.
        
        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            description="GLM-powered GitLab code review bot (Async)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run async general review on current MR
  python review_bot_async.py

  # Run async security review with custom prompt
  python review_bot_async.py --review-type security --custom-prompt "Focus on security vulnerabilities"

  # Run with increased concurrency
  python review_bot_async.py --concurrent-limit 5

  # Process multiple MRs concurrently
  python review_bot_async.py --multiple-mrs "project1:123,project1:124,project2:56"

  # Dry run to see what would be analyzed
  python review_bot_async.py --dry-run
            """
        )
        
        # Basic options
        parser.add_argument(
            "--review-type",
            choices=[rt.value for rt in ReviewType],
            default=ReviewType.GENERAL.value,
            help="Type of code review to perform (default: general)"
        )
        
        parser.add_argument(
            "--custom-prompt",
            type=str,
            help="Custom prompt instructions for GLM analysis"
        )
        
        parser.add_argument(
            "--max-chunks",
            type=int,
            help="Maximum number of diff chunks to process"
        )
        
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run analysis without publishing comments"
        )
        
        # Async-specific options
        parser.add_argument(
            "--concurrent-limit",
            type=int,
            default=3,
            help="Maximum number of concurrent API requests (default: 3)"
        )
        
        parser.add_argument(
            "--multiple-mrs",
            type=str,
            help="Comma-separated list of MRs in format 'project_id:mr_iid'"
        )
        
        parser.add_argument(
            "--concurrent-mrs",
            type=int,
            default=2,
            help="Maximum number of MRs to process concurrently (default: 2)"
        )
        
        parser.add_argument(
            "--chunk-timeout",
            type=int,
            help="Timeout per chunk in seconds (default: 120)"
        )
        
        parser.add_argument(
            "--gitlab-timeout",
            type=int,
            help="GitLab API timeout in seconds (default: 60)"
        )
        
        parser.add_argument(
            "--glm-timeout",
            type=int,
            help="GLM API timeout in seconds (default: 60)"
        )
        
        # Logging options
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO",
            help="Logging level (default: INFO)"
        )
        
        parser.add_argument(
            "--verbose", "-v",
            action="store_true",
            help="Enable verbose logging"
        )
        
        return parser
    
    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command-line arguments.
        
        Args:
            args: List of arguments to parse (defaults to sys.argv)
            
        Returns:
            Parsed arguments namespace
            
        Raises:
            ConfigurationError: If argument validation fails
        """
        parser = self.create_parser()
        parsed_args = parser.parse_args(args)
        
        # Validate arguments
        self._validate_args(parsed_args)
        
        return parsed_args
    
    def _validate_args(self, args: argparse.Namespace) -> None:
        """
        Validate parsed arguments.
        
        Args:
            args: Parsed arguments to validate
            
        Raises:
            ConfigurationError: If validation fails
        """
        if args.concurrent_limit < 1:
            raise ConfigurationError("Concurrent limit must be at least 1")
        
        if args.concurrent_mrs < 1:
            raise ConfigurationError("Concurrent MRs must be at least 1")
        
        if args.max_chunks is not None and args.max_chunks < 1:
            raise ConfigurationError("Max chunks must be at least 1")
        
        if args.multiple_mrs:
            try:
                mr_list = self._parse_multiple_mrs(args.multiple_mrs)
                if not mr_list:
                    raise ConfigurationError("No valid MRs found in multiple-mrs argument")
            except Exception as e:
                raise ConfigurationError(f"Invalid multiple-mrs format: {e}")
    
    def _parse_multiple_mrs(self, mr_string: str) -> List[dict]:
        """
        Parse multiple MRs from string format.
        
        Args:
            mr_string: String in format "project1:mr1,project2:mr2"
            
        Returns:
            List of dictionaries with project_id and mr_iid
        """
        mr_list = []
        if not mr_string:
            return mr_list
        
        for mr_part in mr_string.split(','):
            mr_part = mr_part.strip()
            if not mr_part:
                continue
            
            if ':' not in mr_part:
                raise ValueError(f"Invalid MR format: {mr_part}. Expected 'project_id:mr_iid'")
            
            project_id, mr_iid = mr_part.split(':', 1)
            mr_list.append({
                'project_id': project_id.strip(),
                'mr_iid': mr_iid.strip()
            })
        
        return mr_list
    
    async def execute(self, args: Optional[List[str]] = None) -> int:
        """
        Execute the async review bot with provided arguments.
        
        Args:
            args: Command-line arguments to execute
            
        Returns:
            Exit code (0 for success, 1 for error)
        """
        try:
            # Parse arguments
            parsed_args = self.parse_args(args)
            
            # Setup logging
            log_level = "DEBUG" if parsed_args.verbose else parsed_args.log_level
            setup_logging(level=log_level)
            self.logger = get_logger("async_cli")
            
            self.logger.info("Starting async GLM Code Review Bot")
            self.logger.debug(f"Parsed arguments: {parsed_args}")
            
            # Update settings with CLI arguments
            self._update_settings(parsed_args)
            
            # Execute appropriate async command
            if parsed_args.multiple_mrs:
                return await self._execute_multiple_mrs(parsed_args)
            else:
                return await self._execute_single_mr(parsed_args)
                
        except ReviewBotError as e:
            if self.logger:
                self.logger.error(f"Review bot error: {e}")
            else:
                print(f"Error: {e}", file=sys.stderr)
            return 1
        except Exception as e:
            if self.logger:
                self.logger.error(f"Unexpected error: {e}", exc_info=True)
            else:
                print(f"Unexpected error: {e}", file=sys.stderr)
            return 1
    
    async def _execute_single_mr(self, args: argparse.Namespace) -> int:
        """
        Execute async review for a single MR.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Exit code
        """
        from .review_processor_async import AsyncReviewProcessor
        
        # Create async review processor
        processor = AsyncReviewProcessor(
            self.settings, 
            concurrent_limit=args.concurrent_limit
        )
        
        try:
            self.logger.info("Processing single MR asynchronously")
            
            # Convert review type string to enum
            review_type = ReviewType(args.review_type)
            
            # Process MR
            result = await processor.process_merge_request(
                dry_run=args.dry_run,
                review_type=review_type,
                custom_prompt=args.custom_prompt,
                max_chunks=args.max_chunks
            )
            
            # Log results
            self._log_results(result)
            
            return 0
            
        finally:
            # Cleanup
            if hasattr(processor, 'client_manager'):
                await processor.client_manager.close_all_clients()
    
    async def _execute_multiple_mrs(self, args: argparse.Namespace) -> int:
        """
        Execute async review for multiple MRs.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            Exit code
        """
        from .review_processor_async import AsyncReviewProcessor
        
        # Parse MR list
        mr_list = self._parse_multiple_mrs(args.multiple_mrs)
        
        self.logger.info(f"Processing {len(mr_list)} MRs concurrently")
        
        # Create async review processor
        processor = AsyncReviewProcessor(
            self.settings,
            concurrent_limit=args.concurrent_limit
        )
        
        try:
            # Convert review type string to enum
            review_type = ReviewType(args.review_type)
            
            # Process multiple MRs
            results = await processor.process_multiple_merge_requests(
                mr_list=mr_list,
                dry_run=args.dry_run,
                review_type=review_type,
                custom_prompt=args.custom_prompt,
                max_chunks=args.max_chunks,
                concurrent_mrs=args.concurrent_mrs
            )
            
            # Log results
            self._log_multiple_results(results)
            
            # Return non-zero exit code if any MRs failed
            failed_count = len([r for r in results if not r.get("success")])
            if failed_count > 0:
                self.logger.warning(f"{failed_count} MRs failed to process")
                return 1
            
            return 0
            
        finally:
            # Cleanup
            if hasattr(processor, 'client_manager'):
                await processor.client_manager.close_all_clients()
    
    def _update_settings(self, args: argparse.Namespace) -> None:
        """
        Update settings object with CLI arguments.
        
        Args:
            args: Parsed command-line arguments
        """
        # Update concurrency settings
        if hasattr(self.settings, 'concurrent_glm_requests'):
            self.settings.concurrent_glm_requests = args.concurrent_limit
        if hasattr(self.settings, 'concurrent_mrs'):
            self.settings.concurrent_mrs = args.concurrent_mrs
        
        # Update timeout settings
        if args.chunk_timeout and hasattr(self.settings, 'chunk_timeout'):
            self.settings.chunk_timeout = args.chunk_timeout
        if args.gitlab_timeout and hasattr(self.settings, 'gitlab_timeout'):
            self.settings.gitlab_timeout = args.gitlab_timeout
        if args.glm_timeout and hasattr(self.settings, 'glm_timeout'):
            self.settings.glm_timeout = args.glm_timeout
    
    def _log_results(self, result: dict) -> None:
        """Log processing results."""
        if not self.logger:
            return
        
        stats = result.get("stats", {})
        
        self.logger.info(
            "Review processing completed successfully",
            extra={
                "status": result.get("status"),
                "processing_time": result.get("processing_time"),
                "chunks_processed": stats.get("chunks_processed", 0),
                "comments_generated": stats.get("total_comments_generated", 0),
                "tokens_used": stats.get("total_tokens_used", 0),
                "files_reviewed": stats.get("files_reviewed", 0)
            }
        )
    
    def _log_multiple_results(self, results: List[dict]) -> None:
        """Log multiple MR processing results."""
        if not self.logger:
            return
        
        successful = len([r for r in results if r.get("success")])
        failed = len(results) - successful
        
        self.logger.info(
            f"Multiple MR processing completed: {successful} successful, {failed} failed"
        )
        
        for i, result in enumerate(results):
            mr_data = result.get("mr_data", {})
            status = "SUCCESS" if result.get("success") else "FAILED"
            self.logger.info(
                f"MR {mr_data.get('project_id', 'unknown')}:{mr_data.get('mr_iid', 'unknown')}: {status}"
            )


# Maintain backward compatibility
class CLIHandler(AsyncCLIHandler):
    """
    Synchronous CLI handler for backward compatibility.
    
    This class provides the same interface as the async handler but
    executes async operations in a sync context.
    """
    
    def execute(self, args: Optional[List[str]] = None) -> int:
        """Synchronous wrapper for async method."""
        return asyncio.run(super().execute(args))