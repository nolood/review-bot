"""
Pydantic models for GitLab webhook payloads.

This module defines type-safe models for all GitLab webhook events,
providing automatic validation and serialization/deserialization.

GitLab webhook documentation:
https://docs.gitlab.com/ee/user/project/integrations/webhooks.html
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class WebhookEventType(str, Enum):
    """
    GitLab webhook event types.

    These correspond to the X-Gitlab-Event header values.
    """

    MERGE_REQUEST = "Merge Request Hook"
    PUSH = "Push Hook"
    TAG_PUSH = "Tag Push Hook"
    ISSUE = "Issue Hook"
    NOTE = "Note Hook"
    PIPELINE = "Pipeline Hook"
    WIKI_PAGE = "Wiki Page Hook"
    DEPLOYMENT = "Deployment Hook"
    RELEASE = "Release Hook"


class MergeRequestAction(str, Enum):
    """
    Merge request webhook action types.

    GitLab triggers webhooks for various MR actions.
    """

    OPEN = "open"
    CLOSE = "close"
    REOPEN = "reopen"
    UPDATE = "update"
    APPROVED = "approved"
    UNAPPROVED = "unapproved"
    APPROVAL = "approval"
    UNAPPROVAL = "unapproval"
    MERGE = "merge"


class NoteableType(str, Enum):
    """
    GitLab noteable object types.

    Types of objects that can have notes/comments attached.
    """

    MERGE_REQUEST = "MergeRequest"
    ISSUE = "Issue"
    COMMIT = "Commit"
    SNIPPET = "Snippet"


class GitLabUser(BaseModel):
    """
    GitLab user object.

    Represents a user in GitLab webhook payloads.
    """

    id: int = Field(..., description="User ID")
    name: str = Field(..., description="User display name")
    username: str = Field(..., description="User username")
    email: str | None = Field(None, description="User email address")
    avatar_url: str | None = Field(None, description="User avatar URL")

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class GitLabProject(BaseModel):
    """
    GitLab project object.

    Represents a project in GitLab webhook payloads.
    """

    id: int = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: str | None = Field(None, description="Project description")
    web_url: str = Field(..., description="Project web URL")
    avatar_url: str | None = Field(None, description="Project avatar URL")
    git_ssh_url: str | None = Field(None, description="Git SSH URL")
    git_http_url: str | None = Field(None, description="Git HTTP URL")
    namespace: str = Field(..., description="Project namespace")
    visibility_level: int = Field(..., description="Visibility level (0=private, 10=internal, 20=public)")
    path_with_namespace: str = Field(..., description="Full project path with namespace")
    default_branch: str | None = Field(None, description="Default branch name")
    homepage: str | None = Field(None, description="Project homepage URL")

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class GitLabNote(BaseModel):
    """
    GitLab note/comment object.

    Represents a note/comment in GitLab webhook payloads.
    """

    id: int = Field(..., description="Note ID")
    note: str = Field(..., description="Note content/body")
    noteable_type: str = Field(..., description="Type of noteable object")
    noteable_id: int | None = Field(None, description="ID of noteable object")
    author_id: int = Field(..., description="Note author ID")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    project_id: int = Field(..., description="Project ID")
    discussion_id: str | None = Field(None, description="Discussion thread ID")
    resolvable: bool = Field(False, description="Whether note can be resolved")
    resolved: bool = Field(False, description="Whether note is resolved")
    system: bool = Field(False, description="Whether this is a system note")
    url: str = Field(..., description="Note web URL")
    position: dict[str, Any] | None = Field(None, description="Position data for diff comments")

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class GitLabMergeRequest(BaseModel):
    """
    GitLab merge request object.

    Represents a merge request in webhook payloads.
    """

    id: int = Field(..., description="MR database ID")
    iid: int = Field(..., description="MR internal ID (project-scoped)")
    title: str = Field(..., description="MR title")
    description: str | None = Field(None, description="MR description")
    state: str = Field(..., description="MR state (opened, closed, locked, merged)")
    created_at: str = Field(..., description="Creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
    target_branch: str = Field(..., description="Target branch name")
    source_branch: str = Field(..., description="Source branch name")
    source_project_id: int = Field(..., description="Source project ID")
    target_project_id: int = Field(..., description="Target project ID")
    author_id: int = Field(..., description="Author user ID")
    assignee_id: int | None = Field(None, description="Assignee user ID")
    assignee_ids: list[int] = Field(default_factory=list, description="List of assignee IDs")
    reviewer_ids: list[int] = Field(default_factory=list, description="List of reviewer IDs")
    draft: bool = Field(False, description="Whether MR is a draft/WIP")
    work_in_progress: bool = Field(False, description="Whether MR is work in progress")
    merge_status: str = Field(..., description="Merge status (can_be_merged, cannot_be_merged, unchecked)")
    url: str = Field(..., description="MR web URL")
    labels: list[str] = Field(default_factory=list, description="List of label names")
    last_commit: dict[str, Any] | None = Field(None, description="Last commit information")

    @field_validator("draft", "work_in_progress", mode="before")
    @classmethod
    def parse_boolean(cls, v: Any) -> bool:
        """Parse boolean values from various formats."""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            return v.lower() in ("true", "1", "yes")
        return bool(v)

    @property
    def is_draft(self) -> bool:
        """Check if MR is a draft or WIP."""
        return self.draft or self.work_in_progress

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class MergeRequestChanges(BaseModel):
    """
    Changes in a merge request update.

    GitLab includes changed fields when action is 'update'.
    """

    updated_by_id: dict[str, int | None] | None = Field(None, description="Updated by user ID change")
    updated_at: dict[str, str | None] | None = Field(None, description="Updated at timestamp change")
    labels: dict[str, list[dict[str, Any]]] | None = Field(None, description="Label changes")
    title: dict[str, str | None] | None = Field(None, description="Title change")
    description: dict[str, str | None] | None = Field(None, description="Description change")

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class MergeRequestWebhookPayload(BaseModel):
    """
    GitLab merge request webhook payload.

    Complete structure for MR webhook events.
    """

    object_kind: str = Field(..., description="Event type (always 'merge_request')")
    event_type: str = Field(..., description="Event type name")
    user: GitLabUser = Field(..., description="User who triggered the event")
    project: GitLabProject = Field(..., description="Target project")
    repository: dict[str, Any] | None = Field(None, description="Repository information")
    object_attributes: GitLabMergeRequest = Field(..., description="Merge request details")
    labels: list[dict[str, Any]] = Field(default_factory=list, description="MR labels")
    changes: MergeRequestChanges | None = Field(None, description="Changes (for update action)")
    assignees: list[GitLabUser] = Field(default_factory=list, description="Assignee users")
    reviewers: list[GitLabUser] = Field(default_factory=list, description="Reviewer users")

    @field_validator("object_kind")
    @classmethod
    def validate_object_kind(cls, v: str) -> str:
        """Validate that object_kind is 'merge_request'."""
        if v != "merge_request":
            raise ValueError(f"Expected object_kind 'merge_request', got '{v}'")
        return v

    @property
    def action(self) -> str:
        """Get the merge request action from object_attributes."""
        return getattr(self.object_attributes, "action", "unknown")

    @property
    def mr_iid(self) -> int:
        """Get the merge request IID."""
        return self.object_attributes.iid

    @property
    def project_id(self) -> int:
        """Get the target project ID."""
        return self.project.id

    @property
    def source_branch(self) -> str:
        """Get the source branch name."""
        return self.object_attributes.source_branch

    @property
    def target_branch(self) -> str:
        """Get the target branch name."""
        return self.object_attributes.target_branch

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class PushCommit(BaseModel):
    """
    Git commit in a push event.

    Represents individual commits in push webhooks.
    """

    id: str = Field(..., description="Commit SHA")
    message: str = Field(..., description="Commit message")
    title: str | None = Field(None, description="Commit title (first line)")
    timestamp: str = Field(..., description="Commit timestamp")
    url: str = Field(..., description="Commit web URL")
    author: dict[str, str] = Field(..., description="Commit author info")
    added: list[str] = Field(default_factory=list, description="Added files")
    modified: list[str] = Field(default_factory=list, description="Modified files")
    removed: list[str] = Field(default_factory=list, description="Removed files")

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class PushWebhookPayload(BaseModel):
    """
    GitLab push webhook payload.

    Complete structure for push webhook events.
    """

    object_kind: str = Field(..., description="Event type (always 'push')")
    event_name: str = Field(..., description="Event name")
    before: str = Field(..., description="SHA before push")
    after: str = Field(..., description="SHA after push")
    ref: str = Field(..., description="Full ref name (refs/heads/branch)")
    checkout_sha: str | None = Field(None, description="SHA to checkout")
    user_id: int = Field(..., description="User ID who pushed")
    user_name: str = Field(..., description="User name who pushed")
    user_username: str = Field(..., description="Username who pushed")
    user_email: str = Field(..., description="Email of user who pushed")
    user_avatar: str | None = Field(None, description="Avatar URL of user")
    project_id: int = Field(..., description="Project ID")
    project: GitLabProject = Field(..., description="Project details")
    repository: dict[str, Any] = Field(..., description="Repository information")
    commits: list[PushCommit] = Field(default_factory=list, description="List of commits")
    total_commits_count: int = Field(..., description="Total number of commits")

    @field_validator("object_kind")
    @classmethod
    def validate_object_kind(cls, v: str) -> str:
        """Validate that object_kind is 'push'."""
        if v != "push":
            raise ValueError(f"Expected object_kind 'push', got '{v}'")
        return v

    @property
    def branch_name(self) -> str:
        """Extract branch name from ref."""
        # refs/heads/main -> main
        if self.ref.startswith("refs/heads/"):
            return self.ref[11:]
        return self.ref

    @property
    def is_new_branch(self) -> bool:
        """Check if this push creates a new branch."""
        return self.before == "0000000000000000000000000000000000000000"

    @property
    def is_deleted_branch(self) -> bool:
        """Check if this push deletes a branch."""
        return self.after == "0000000000000000000000000000000000000000"

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class NoteWebhookPayload(BaseModel):
    """
    GitLab note/comment webhook payload.

    Complete structure for note webhook events (comments on MRs, issues, commits, snippets).
    """

    object_kind: str = Field(..., description="Event type (always 'note')")
    event_type: str = Field(..., description="Event type name")
    user: GitLabUser = Field(..., description="User who triggered the event")
    project_id: int = Field(..., description="Project ID")
    project: GitLabProject = Field(..., description="Project details")
    object_attributes: GitLabNote = Field(..., description="Note details")
    merge_request: GitLabMergeRequest | None = Field(
        None, description="MR details if note on MR"
    )

    @field_validator("object_kind")
    @classmethod
    def validate_object_kind(cls, v: str) -> str:
        """Validate that object_kind is 'note'."""
        if v != "note":
            raise ValueError(f"Expected object_kind 'note', got '{v}'")
        return v

    @property
    def is_merge_request_note(self) -> bool:
        """Check if note is on a merge request."""
        return self.object_attributes.noteable_type == "MergeRequest"

    @property
    def is_discussion_note(self) -> bool:
        """Check if note is part of a discussion thread."""
        return self.object_attributes.discussion_id is not None

    @property
    def note_body(self) -> str:
        """Get note content."""
        return self.object_attributes.note

    @property
    def discussion_id(self) -> str | None:
        """Get discussion ID."""
        return self.object_attributes.discussion_id

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"


class WebhookValidationResult(BaseModel):
    """
    Result of webhook validation.

    Contains validation status and reasons for rejection.
    """

    is_valid: bool = Field(..., description="Whether webhook is valid")
    event_type: WebhookEventType | None = Field(None, description="Validated event type")
    should_process: bool = Field(False, description="Whether event should be processed")
    rejection_reason: str | None = Field(None, description="Reason for rejection if not valid")
    payload: (
        MergeRequestWebhookPayload | PushWebhookPayload | NoteWebhookPayload | None
    ) = Field(None, description="Parsed webhook payload")

    class Config:
        """Pydantic configuration."""

        frozen = False
        extra = "allow"
