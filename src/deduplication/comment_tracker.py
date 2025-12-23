"""
Comment tracking and deduplication for GitLab merge requests.

This module provides functionality for tracking bot comments and applying
different deduplication strategies to clean up old comments before posting
new review feedback.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from ..gitlab_client import GitLabClient
from ..utils.logger import get_logger


class DeduplicationStrategy(Enum):
    """Strategies for handling duplicate comments on merge requests."""

    DELETE_ALL = "delete_all"  # Delete all previous bot comments
    DELETE_SUMMARY_ONLY = "delete_summary_only"  # Delete only summary comments
    KEEP_ALL = "keep_all"  # Keep all previous comments
    DELETE_OUTDATED = "delete_outdated"  # Delete comments from previous commits


@dataclass
class TrackedComment:
    """
    Represents a tracked comment on a merge request.

    Attributes:
        comment_id: Unique identifier for the comment
        note_id: GitLab note ID (for simple comments)
        discussion_id: GitLab discussion ID (for inline comments)
        body: Comment text content
        author_username: Username of the comment author
        created_at: Timestamp when comment was created
        is_system: Whether this is a system-generated comment
        is_inline: Whether this is an inline code comment
        file_path: File path for inline comments
        line_number: Line number for inline comments
    """

    comment_id: str
    note_id: int | None
    discussion_id: str | None
    body: str
    author_username: str
    created_at: datetime
    is_system: bool = False
    is_inline: bool = False
    file_path: str | None = None
    line_number: int | None = None


@dataclass
class DeduplicationResult:
    """
    Result of a deduplication operation.

    Attributes:
        deleted_count: Number of comments successfully deleted
        failed_count: Number of deletions that failed
        kept_count: Number of comments kept (not deleted)
        deleted_ids: List of IDs for deleted comments
        failed_ids: List of IDs for failed deletions
        errors: List of error messages encountered
    """

    deleted_count: int = 0
    failed_count: int = 0
    kept_count: int = 0
    deleted_ids: list[str] = field(default_factory=list)
    failed_ids: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def add_success(self, comment_id: str) -> None:
        """Record a successful deletion."""
        self.deleted_count += 1
        self.deleted_ids.append(comment_id)

    def add_failure(self, comment_id: str, error: str) -> None:
        """Record a failed deletion."""
        self.failed_count += 1
        self.failed_ids.append(comment_id)
        self.errors.append(error)

    def add_kept(self) -> None:
        """Record a comment that was kept."""
        self.kept_count += 1


class CommentTracker:
    """
    Tracks and manages bot comments on GitLab merge requests.

    This class provides functionality to list bot comments, apply deduplication
    strategies, and clean up old comments before posting new review feedback.
    """

    def __init__(
        self,
        gitlab_client: GitLabClient,
        bot_username: str | None = None,
        bot_user_id: int | None = None,
    ):
        """
        Initialize comment tracker.

        Args:
            gitlab_client: GitLab API client instance
            bot_username: Username of the bot (used to identify bot comments)
            bot_user_id: User ID of the bot (alternative to username)
        """
        self.gitlab_client = gitlab_client
        self.bot_username = bot_username or "glm-review-bot"
        self.bot_user_id = bot_user_id
        self.logger = get_logger(__name__)

    async def get_bot_comments(
        self,
        project_id: str,
        mr_iid: str,
        include_inline: bool = True,
        include_summary: bool = True,
    ) -> list[TrackedComment]:
        """
        Get all bot comments on a merge request.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            include_inline: Include inline code comments
            include_summary: Include summary/general comments

        Returns:
            List of tracked comments from the bot

        Raises:
            GitLabAPIError: If comment retrieval fails
        """
        comments: list[TrackedComment] = []

        try:
            # Get general comments (notes)
            if include_summary:
                notes = await self._fetch_notes(project_id, mr_iid)
                comments.extend(notes)

            # Get inline comments (discussions)
            if include_inline:
                discussions = await self._fetch_discussions(project_id, mr_iid)
                comments.extend(discussions)

            self.logger.info(
                "Retrieved bot comments",
                extra={
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "total_comments": len(comments),
                    "include_inline": include_inline,
                    "include_summary": include_summary,
                },
            )

            return comments

        except Exception as e:
            self.logger.error(
                f"Failed to retrieve bot comments: {str(e)}",
                extra={"project_id": project_id, "mr_iid": mr_iid},
            )
            raise

    async def cleanup_old_comments(
        self,
        project_id: str,
        mr_iid: str,
        strategy: DeduplicationStrategy = DeduplicationStrategy.DELETE_ALL,
        current_commit_sha: str | None = None,
    ) -> DeduplicationResult:
        """
        Clean up old bot comments based on deduplication strategy.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            strategy: Deduplication strategy to apply
            current_commit_sha: Current commit SHA (for DELETE_OUTDATED strategy)

        Returns:
            Result of the deduplication operation

        Raises:
            ValueError: If strategy requires commit_sha but none provided
        """
        result = DeduplicationResult()

        # KEEP_ALL strategy doesn't delete anything
        if strategy == DeduplicationStrategy.KEEP_ALL:
            self.logger.info(
                "Using KEEP_ALL strategy, no comments will be deleted",
                extra={"project_id": project_id, "mr_iid": mr_iid},
            )
            return result

        # Validate DELETE_OUTDATED requirements
        if strategy == DeduplicationStrategy.DELETE_OUTDATED and not current_commit_sha:
            raise ValueError(
                "DELETE_OUTDATED strategy requires current_commit_sha parameter"
            )

        try:
            # Determine which comments to include based on strategy
            include_inline = strategy in [
                DeduplicationStrategy.DELETE_ALL,
                DeduplicationStrategy.DELETE_OUTDATED,
            ]
            include_summary = True  # Always check summary comments

            # Get existing bot comments
            comments = await self.get_bot_comments(
                project_id=project_id,
                mr_iid=mr_iid,
                include_inline=include_inline,
                include_summary=include_summary,
            )

            # Filter comments based on strategy
            comments_to_delete = self._filter_comments_by_strategy(
                comments, strategy, current_commit_sha
            )

            self.logger.info(
                "Applying deduplication strategy",
                extra={
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "strategy": strategy.value,
                    "total_comments": len(comments),
                    "to_delete": len(comments_to_delete),
                    "to_keep": len(comments) - len(comments_to_delete),
                },
            )

            # Delete filtered comments
            for comment in comments_to_delete:
                await self._delete_comment(project_id, mr_iid, comment, result)

            # Count kept comments
            result.kept_count = len(comments) - len(comments_to_delete)

            self.logger.info(
                "Deduplication completed",
                extra={
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "deleted": result.deleted_count,
                    "failed": result.failed_count,
                    "kept": result.kept_count,
                },
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Deduplication failed: {str(e)}",
                extra={"project_id": project_id, "mr_iid": mr_iid},
            )
            raise

    async def _fetch_notes(
        self, project_id: str, mr_iid: str
    ) -> list[TrackedComment]:
        """
        Fetch general comments (notes) from merge request.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID

        Returns:
            List of tracked comments from notes
        """
        url = f"{self.gitlab_client.api_url}/projects/{project_id}/merge_requests/{mr_iid}/notes"

        try:
            async with self.gitlab_client.get_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                notes_data = response.json()

            tracked_comments = []
            for note in notes_data:
                # Skip system notes
                if note.get("system", False):
                    continue

                # Filter by bot username or user ID
                author = note.get("author", {})
                if not self._is_bot_comment(author):
                    continue

                tracked_comment = TrackedComment(
                    comment_id=f"note_{note['id']}",
                    note_id=note["id"],
                    discussion_id=None,
                    body=note.get("body", ""),
                    author_username=author.get("username", ""),
                    created_at=datetime.fromisoformat(
                        note.get("created_at", "").replace("Z", "+00:00")
                    ),
                    is_system=False,
                    is_inline=False,
                )
                tracked_comments.append(tracked_comment)

            self.logger.debug(
                f"Fetched {len(tracked_comments)} bot notes",
                extra={"project_id": project_id, "mr_iid": mr_iid},
            )

            return tracked_comments

        except Exception as e:
            self.logger.error(
                f"Failed to fetch notes: {str(e)}",
                extra={"project_id": project_id, "mr_iid": mr_iid},
            )
            return []

    async def _fetch_discussions(
        self, project_id: str, mr_iid: str
    ) -> list[TrackedComment]:
        """
        Fetch inline comments (discussions) from merge request.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID

        Returns:
            List of tracked comments from discussions
        """
        url = f"{self.gitlab_client.api_url}/projects/{project_id}/merge_requests/{mr_iid}/discussions"

        try:
            async with self.gitlab_client.get_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                discussions_data = response.json()

            tracked_comments = []
            for discussion in discussions_data:
                notes = discussion.get("notes", [])

                # Process each note in the discussion
                for note in notes:
                    # Skip system notes
                    if note.get("system", False):
                        continue

                    # Filter by bot username or user ID
                    author = note.get("author", {})
                    if not self._is_bot_comment(author):
                        continue

                    # Extract position information for inline comments
                    position = note.get("position", {})
                    is_inline = bool(position)
                    file_path = position.get("new_path") if is_inline else None
                    line_number = position.get("new_line") if is_inline else None

                    tracked_comment = TrackedComment(
                        comment_id=f"discussion_{discussion['id']}_note_{note['id']}",
                        note_id=note["id"],
                        discussion_id=discussion["id"],
                        body=note.get("body", ""),
                        author_username=author.get("username", ""),
                        created_at=datetime.fromisoformat(
                            note.get("created_at", "").replace("Z", "+00:00")
                        ),
                        is_system=False,
                        is_inline=is_inline,
                        file_path=file_path,
                        line_number=line_number,
                    )
                    tracked_comments.append(tracked_comment)

            self.logger.debug(
                f"Fetched {len(tracked_comments)} bot discussion notes",
                extra={"project_id": project_id, "mr_iid": mr_iid},
            )

            return tracked_comments

        except Exception as e:
            self.logger.error(
                f"Failed to fetch discussions: {str(e)}",
                extra={"project_id": project_id, "mr_iid": mr_iid},
            )
            return []

    def _is_bot_comment(self, author: dict[str, Any]) -> bool:
        """
        Check if a comment was made by the bot.

        Args:
            author: Author information from GitLab API

        Returns:
            True if comment is from the bot
        """
        if self.bot_user_id and author.get("id") == self.bot_user_id:
            return True

        if self.bot_username and author.get("username") == self.bot_username:
            return True

        return False

    def _filter_comments_by_strategy(
        self,
        comments: list[TrackedComment],
        strategy: DeduplicationStrategy,
        current_commit_sha: str | None = None,
    ) -> list[TrackedComment]:
        """
        Filter comments based on deduplication strategy.

        Args:
            comments: List of all bot comments
            strategy: Deduplication strategy to apply
            current_commit_sha: Current commit SHA (for DELETE_OUTDATED)

        Returns:
            List of comments to delete
        """
        if strategy == DeduplicationStrategy.DELETE_ALL:
            return comments

        if strategy == DeduplicationStrategy.DELETE_SUMMARY_ONLY:
            return [c for c in comments if not c.is_inline]

        if strategy == DeduplicationStrategy.DELETE_OUTDATED:
            # For now, delete all comments as we don't track commit associations
            # This can be enhanced with commit tracking from CommitTracker
            return comments

        # KEEP_ALL - return empty list
        return []

    async def _delete_comment(
        self,
        project_id: str,
        mr_iid: str,
        comment: TrackedComment,
        result: DeduplicationResult,
    ) -> None:
        """
        Delete a single comment from GitLab.

        Args:
            project_id: GitLab project ID
            mr_iid: Merge request IID
            comment: Comment to delete
            result: Result object to update with deletion outcome
        """
        try:
            if comment.discussion_id:
                # Delete discussion note
                url = (
                    f"{self.gitlab_client.api_url}/projects/{project_id}/"
                    f"merge_requests/{mr_iid}/discussions/{comment.discussion_id}/"
                    f"notes/{comment.note_id}"
                )
            else:
                # Delete simple note
                url = (
                    f"{self.gitlab_client.api_url}/projects/{project_id}/"
                    f"merge_requests/{mr_iid}/notes/{comment.note_id}"
                )

            async with self.gitlab_client.get_client() as client:
                response = await client.delete(url)
                response.raise_for_status()

            result.add_success(comment.comment_id)
            self.logger.debug(
                f"Deleted comment: {comment.comment_id}",
                extra={
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "is_inline": comment.is_inline,
                },
            )

        except Exception as e:
            error_msg = f"Failed to delete {comment.comment_id}: {str(e)}"
            result.add_failure(comment.comment_id, error_msg)
            self.logger.warning(
                error_msg,
                extra={
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "comment_id": comment.comment_id,
                },
            )
