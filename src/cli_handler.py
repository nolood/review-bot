"""
CLI Handler for the GLM Code Review Bot.

This module handles command-line argument parsing and validation
for the review bot application.
"""

import argparse
import sys
from typing import Optional, List

from .config.prompts import ReviewType
from .utils.logger import get_logger, setup_logging
from .utils.exceptions import ReviewBotError, ConfigurationError


class CLIHandler:
    """
    Handles command-line interface and execution for the review bot.
    
    This class is responsible for:
    - Parsing and validating command-line arguments
    - Setting up logging configuration
    - Providing a clean interface for CLI operations
    """
    
    def __init__(self, settings):
        """
        Initialize the CLI handler with settings.
        
        Args:
            settings: Application settings instance
        """
        self.settings = settings
        self.logger = None
    
    def create_parser(self) -> argparse.ArgumentParser:
        """
        Create and configure the argument parser.
        
        Returns:
            Configured ArgumentParser instance
        """
        parser = argparse.ArgumentParser(
            description="GLM-powered GitLab code review bot",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Run general review on current MR
  python review_bot.py
  
  # Run security-focused review
  python review_bot.py --type security
  
  # Run with custom prompt (dry run)
  python review_bot.py --dry-run --custom-prompt "Focus on error handling"
  
  # Limit processing to first 3 chunks
  python review_bot.py --max-chunks 3
            """
        )
        
        # Review type selection
        parser.add_argument(
            "--type",
            choices=["general", "security", "performance"],
            default="general",
            help="Type of review to perform (default: general)"
        )
        
        # Custom prompt
        parser.add_argument(
            "--custom-prompt",
            type=str,
            help="Custom prompt instructions for the review"
        )
        
        # Dry run mode
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Run analysis without publishing comments"
        )
        
        # Chunk limiting
        parser.add_argument(
            "--max-chunks",
            type=int,
            help="Maximum number of diff chunks to process"
        )
        
        # Logging options
        parser.add_argument(
            "--log-level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
            help="Override logging level"
        )
        
        parser.add_argument(
            "--log-format",
            choices=["text", "json"],
            help="Override log format"
        )
        
        parser.add_argument(
            "--log-file",
            type=str,
            help="Log to file instead of console"
        )
        
        # Validation only mode
        parser.add_argument(
            "--validate-only",
            action="store_true",
            help="Only validate environment and exit"
        )
        
        return parser
    
    def setup_logging(self, args: argparse.Namespace) -> bool:
        """
        Setup logging with command-line overrides.
        
        Args:
            args: Parsed command-line arguments
            
        Returns:
            True if logging setup succeeded, False otherwise
        """
        try:
            setup_logging(
                level=args.log_level or getattr(self.settings, 'log_level', 'INFO'),
                format_type=args.log_format or getattr(self.settings, 'log_format', 'text'),
                log_file=args.log_file or getattr(self.settings, 'log_file', None)
            )
            self.logger = get_logger("cli")
            return True
        except Exception as e:
            print(f"Failed to setup logging: {e}", file=sys.stderr)
            return False
    
    def validate_environment(self, dry_run: bool = False) -> None:
        """
        Validate environment configuration.
        
        Args:
            dry_run: Whether this is a dry run (relaxes some requirements)
            
        Raises:
            ConfigurationError: If validation fails
        """
        # This will be implemented to use the existing validation logic
        # For now, we'll delegate to the main validation function
        pass
    
    def parse_review_type(self, type_str: str) -> ReviewType:
        """
        Parse review type string to enum.
        
        Args:
            type_str: Review type string from CLI
            
        Returns:
            ReviewType enum value
            
        Raises:
            ValueError: If review type is invalid
        """
        try:
            return ReviewType(type_str)
        except ValueError as e:
            raise ValueError(f"Invalid review type: {type_str}") from e
    
    def print_success_summary(self, result: dict, dry_run: bool) -> None:
        """
        Print a success summary to stdout for CI/CD integration.
        
        Args:
            result: Processing result dictionary
            dry_run: Whether this was a dry run
        """
        print(f"✅ Review completed in {result['processing_time']:.2f}s")
        stats = result.get("stats", {})
        if stats.get("total_comments_generated", 0) > 0:
            print(f"📝 Generated {stats['total_comments_generated']} comments")
            if not dry_run:
                published = stats.get("file_comments_published", 0) + stats.get("inline_comments_published", 0)
                print(f"📤 Published {published} comments")
    
    def parse_args(self, argv: Optional[List[str]] = None) -> argparse.Namespace:
        """
        Parse command-line arguments.
        
        Args:
            argv: List of command-line arguments (uses sys.argv if None)
            
        Returns:
            Parsed arguments namespace
        """
        parser = self.create_parser()
        return parser.parse_args(argv)
    
    def validate_args(self, args: argparse.Namespace) -> None:
        """
        Validate parsed command-line arguments.
        
        Args:
            args: Parsed arguments
            
        Raises:
            ConfigurationError: If arguments are invalid
        """
        if args.max_chunks is not None and args.max_chunks <= 0:
            raise ConfigurationError("max-chunks must be a positive integer")
        
        if args.custom_prompt and len(args.custom_prompt.strip()) == 0:
            raise ConfigurationError("custom-prompt cannot be empty")