#!/usr/bin/env python3
"""
Async GLM Code Review Bot for GitLab CI/CD.

This is the main entry point for the async version of the GLM Code Review Bot.
It provides concurrent processing capabilities for improved performance.

Usage:
    python review_bot_async.py [options]

Examples:
    # Run async general review on current MR
    python review_bot_async.py

    # Run async security review with increased concurrency
    python review_bot_async.py --review-type security --concurrent-limit 5

    # Process multiple MRs concurrently
    python review_bot_async.py --multiple-mrs "project1:123,project1:124"

    # Dry run to test without publishing
    python review_bot_async.py --dry-run --verbose
"""

import sys
import asyncio
from pathlib import Path

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.config.settings import get_settings
from src.cli_handler_async import AsyncCLIHandler


async def main() -> int:
    """
    Main async entry point for the review bot.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    try:
        # Get settings
        settings = get_settings()
        
        # Create CLI handler and execute
        cli_handler = AsyncCLIHandler(settings)
        return await cli_handler.execute()
        
    except KeyboardInterrupt:
        print("\nReview bot interrupted by user", file=sys.stderr)
        return 130  # Standard exit code for SIGINT
    except Exception as e:
        print(f"Fatal error: {e}", file=sys.stderr)
        return 1


def main_sync() -> int:
    """
    Synchronous wrapper for main entry point.
    
    Returns:
        Exit code (0 for success, 1 for error)
    """
    return asyncio.run(main())


if __name__ == "__main__":
    sys.exit(main_sync())