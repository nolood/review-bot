"""
Deduplication package for comment tracking and cleanup.

This package provides functionality for:
- Tracking bot comments on merge requests
- Deduplicating comments using multiple strategies
- Tracking reviewed commits to avoid duplicate reviews
- Cleaning up old comments before posting new ones
"""

from .comment_tracker import (
    CommentTracker,
    DeduplicationStrategy,
    TrackedComment,
    DeduplicationResult,
)
from .commit_tracker import CommitTracker, ReviewedCommit

__all__ = [
    "CommentTracker",
    "DeduplicationStrategy",
    "TrackedComment",
    "DeduplicationResult",
    "CommitTracker",
    "ReviewedCommit",
]
