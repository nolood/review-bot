"""
Commit tracking for avoiding duplicate code reviews.

This module provides functionality for tracking which commits have been
reviewed to avoid re-reviewing the same code multiple times.
"""

import time
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from ..utils.logger import get_logger


@dataclass
class ReviewedCommit:
    """
    Represents a commit that has been reviewed.

    Attributes:
        commit_sha: Git commit SHA hash
        project_id: GitLab project ID
        mr_iid: Merge request IID
        reviewed_at: Timestamp when the commit was reviewed
        comment_count: Number of review comments posted for this commit
    """

    commit_sha: str
    project_id: str
    mr_iid: str
    reviewed_at: datetime
    comment_count: int = 0


class CommitTracker:
    """
    In-memory tracker for reviewed commits with TTL-based expiration.

    This class maintains a cache of reviewed commits to prevent duplicate
    reviews on the same code. Entries automatically expire after a
    configurable time period.
    """

    def __init__(self, ttl_seconds: int = 86400):
        """
        Initialize commit tracker.

        Args:
            ttl_seconds: Time-to-live for tracked commits in seconds (default: 24 hours)
        """
        self.ttl_seconds = ttl_seconds
        self.logger = get_logger(__name__)

        # Storage: {key -> ReviewedCommit}
        # Key format: "project_id:mr_iid:commit_sha"
        self._storage: dict[str, ReviewedCommit] = {}

        # Expiration tracking: {key -> expiration_timestamp}
        self._expiration: dict[str, float] = {}

        self.logger.info(
            "CommitTracker initialized",
            extra={"ttl_seconds": ttl_seconds, "ttl_hours": ttl_seconds / 3600},
        )

    def is_commit_reviewed(
        self, project_id: str, mr_iid: str, commit_sha: str
    ) -> bool:
        """
        Check if a commit has already been reviewed.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            commit_sha: Git commit SHA hash

        Returns:
            True if commit has been reviewed and not expired
        """
        self._cleanup_expired()

        key = self._make_key(project_id, mr_iid, commit_sha)
        is_reviewed = key in self._storage

        self.logger.debug(
            f"Commit review check: {commit_sha[:8]}",
            extra={
                "project_id": project_id,
                "mr_iid": mr_iid,
                "commit_sha": commit_sha,
                "is_reviewed": is_reviewed,
            },
        )

        return is_reviewed

    def mark_commit_reviewed(
        self, project_id: str, mr_iid: str, commit_sha: str, comment_count: int = 0
    ) -> None:
        """
        Mark a commit as reviewed.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            commit_sha: Git commit SHA hash
            comment_count: Number of comments posted for this commit
        """
        key = self._make_key(project_id, mr_iid, commit_sha)

        reviewed_commit = ReviewedCommit(
            commit_sha=commit_sha,
            project_id=project_id,
            mr_iid=mr_iid,
            reviewed_at=datetime.utcnow(),
            comment_count=comment_count,
        )

        self._storage[key] = reviewed_commit
        self._expiration[key] = time.time() + self.ttl_seconds

        self.logger.info(
            f"Marked commit as reviewed: {commit_sha[:8]}",
            extra={
                "project_id": project_id,
                "mr_iid": mr_iid,
                "commit_sha": commit_sha,
                "comment_count": comment_count,
            },
        )

    def get_last_reviewed(
        self, project_id: str, mr_iid: str, commit_sha: str
    ) -> Optional[ReviewedCommit]:
        """
        Get information about a reviewed commit.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            commit_sha: Git commit SHA hash

        Returns:
            ReviewedCommit if found and not expired, None otherwise
        """
        self._cleanup_expired()

        key = self._make_key(project_id, mr_iid, commit_sha)
        return self._storage.get(key)

    def clear_mr_history(self, project_id: str, mr_iid: str) -> int:
        """
        Clear all tracked commits for a specific merge request.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID

        Returns:
            Number of commits cleared
        """
        prefix = f"{project_id}:{mr_iid}:"
        keys_to_remove = [key for key in self._storage.keys() if key.startswith(prefix)]

        for key in keys_to_remove:
            del self._storage[key]
            if key in self._expiration:
                del self._expiration[key]

        self.logger.info(
            f"Cleared MR history: {len(keys_to_remove)} commits",
            extra={"project_id": project_id, "mr_iid": mr_iid, "cleared": len(keys_to_remove)},
        )

        return len(keys_to_remove)

    def get_tracked_commits_count(self, project_id: str | None = None, mr_iid: str | None = None) -> int:
        """
        Get count of currently tracked commits.

        Args:
            project_id: Optional project ID filter
            mr_iid: Optional MR IID filter (requires project_id)

        Returns:
            Number of tracked commits matching the filter
        """
        self._cleanup_expired()

        if project_id and mr_iid:
            prefix = f"{project_id}:{mr_iid}:"
            return sum(1 for key in self._storage.keys() if key.startswith(prefix))
        elif project_id:
            prefix = f"{project_id}:"
            return sum(1 for key in self._storage.keys() if key.startswith(prefix))
        else:
            return len(self._storage)

    def get_all_tracked_commits(
        self, project_id: str | None = None, mr_iid: str | None = None
    ) -> list[ReviewedCommit]:
        """
        Get all tracked commits, optionally filtered by project/MR.

        Args:
            project_id: Optional project ID filter
            mr_iid: Optional MR IID filter (requires project_id)

        Returns:
            List of ReviewedCommit objects
        """
        self._cleanup_expired()

        if project_id and mr_iid:
            prefix = f"{project_id}:{mr_iid}:"
            return [
                commit
                for key, commit in self._storage.items()
                if key.startswith(prefix)
            ]
        elif project_id:
            prefix = f"{project_id}:"
            return [
                commit
                for key, commit in self._storage.items()
                if key.startswith(prefix)
            ]
        else:
            return list(self._storage.values())

    def clear_all(self) -> int:
        """
        Clear all tracked commits.

        Returns:
            Number of commits cleared
        """
        count = len(self._storage)
        self._storage.clear()
        self._expiration.clear()

        self.logger.info(
            f"Cleared all tracked commits: {count}",
            extra={"cleared_count": count},
        )

        return count

    def _make_key(self, project_id: str, mr_iid: str, commit_sha: str) -> str:
        """
        Create a unique key for a commit.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            commit_sha: Git commit SHA hash

        Returns:
            Unique key string
        """
        return f"{project_id}:{mr_iid}:{commit_sha}"

    def _cleanup_expired(self) -> None:
        """
        Remove expired entries from storage.

        This method is called automatically before read operations
        to ensure expired entries are cleaned up.
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, expiration_time in self._expiration.items()
            if expiration_time <= current_time
        ]

        if expired_keys:
            for key in expired_keys:
                if key in self._storage:
                    del self._storage[key]
                del self._expiration[key]

            self.logger.debug(
                f"Cleaned up {len(expired_keys)} expired commits",
                extra={"expired_count": len(expired_keys)},
            )

    def get_stats(self) -> dict[str, int]:
        """
        Get statistics about the commit tracker.

        Returns:
            Dictionary with tracker statistics
        """
        self._cleanup_expired()

        return {
            "total_tracked": len(self._storage),
            "ttl_seconds": self.ttl_seconds,
            "ttl_hours": self.ttl_seconds // 3600,
        }
