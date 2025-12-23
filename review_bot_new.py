#!/usr/bin/env python3
"""
GLM Code Review Bot - Refactored Main Entry Point

This script orchestrates the code review process using the refactored modular architecture.
"""

import sys
from pathlib import Path

# Add src directory to Python path for imports
src_path = Path(__file__).parent / "src"
if src_path.exists():
    sys.path.insert(0, str(src_path))

from src.cli_handler import CLIHandler
from src.review_processor import ReviewProcessor
from src.config_manager import ConfigurationManager
from src.config.settings import settings
from src.utils.logger import setup_logging
from src.utils.exceptions import ReviewBotError, ConfigurationError


class ReviewBotApp:
    """
    Main application class that orchestrates the review bot.
    
    This class ties together all the refactored components:
    - CLI Handler for argument parsing
    - Configuration Manager for settings validation
    - Review Processor for main logic
    """
    
    def __init__(self):
        """Initialize the application."""
        self.settings = settings
        self.config_manager = ConfigurationManager(self.settings)
        self.cli_handler = CLIHandler(self.settings)
        self.review_processor = None
    
    def run(self, argv=None) -> int:
        """
        Run the review bot application.
        
        Args:
            argv: Command line arguments (uses sys.argv if None)
            
        Returns:
            Exit code
        """
        try:
            # Parse command line arguments
            args = self.cli_handler.parse_args(argv)
            
            # Setup logging
            if not self.cli_handler.setup_logging(args):
                return 1
            
            # Validate arguments
            self.cli_handler.validate_args(args)
            
            # Validate environment
            self.config_manager.validate_environment(dry_run=args.dry_run)
            
            if args.validate_only:
                self.cli_handler.logger.info("Environment validation completed successfully")
                return 0
            
            # Parse review type
            review_type = self.cli_handler.parse_review_type(args.type)
            
            # Initialize review processor
            self.review_processor = ReviewProcessor(self.settings)
            
            # Process the merge request
            result = self.review_processor.process_merge_request(
                dry_run=args.dry_run,
                review_type=review_type,
                custom_prompt=args.custom_prompt,
                max_chunks=args.max_chunks
            )
            
            # Handle results
            if result["status"] == "success":
                self.cli_handler.print_success_summary(result, args.dry_run)
                return 0
            else:
                if self.cli_handler.logger:
                    self.cli_handler.logger.error(
                        f"Review processing failed: {result.get('message', 'Unknown error')}"
                    )
                return 1
                
        except KeyboardInterrupt:
            if hasattr(self.cli_handler, 'logger') and self.cli_handler.logger:
                self.cli_handler.logger.info("Review processing interrupted by user")
            return 130
        except ReviewBotError as e:
            if hasattr(self.cli_handler, 'logger') and self.cli_handler.logger:
                self.cli_handler.logger.error(f"Review bot error: {e}")
            return 1
        except Exception as e:
            if hasattr(self.cli_handler, 'logger') and self.cli_handler.logger:
                self.cli_handler.logger.error(f"Unexpected error: {e}", exc_info=True)
            return 1


def main() -> int:
    """Main entry point for the GLM Code Review Bot."""
    app = ReviewBotApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())