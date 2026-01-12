"""
Webhook validation and filtering logic.

This module provides signature validation, event filtering, and
webhook payload validation for GitLab webhooks.

Key features:
    - Simple token-based signature validation (GitLab style)
    - Event type filtering
    - Draft/WIP filtering
    - Label-based filtering
    - Branch filtering
"""

import hmac
import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from pydantic import ValidationError

from ..utils.exceptions import ReviewBotError
from ..utils.logger import get_logger
from .models import (
    WebhookEventType,
    MergeRequestAction,
    MergeRequestWebhookPayload,
    PushWebhookPayload,
    NoteWebhookPayload,
    WebhookValidationResult,
)

logger = get_logger(__name__)


class WebhookValidationError(ReviewBotError):
    """
    Raised when webhook validation fails.

    This includes signature validation failures, invalid payloads,
    unsupported event types, etc.
    """

    def __init__(
        self,
        message: str,
        event_type: str | None = None,
        validation_error: Exception | None = None,
    ):
        """Initialize webhook validation error."""
        details: dict[str, Any] = {}
        if event_type:
            details["event_type"] = event_type
        if validation_error:
            details["validation_error"] = str(validation_error)

        super().__init__(
            message=message,
            error_code="WEBHOOK_VALIDATION_ERROR",
            details=details,
        )


@dataclass
class WebhookConfig:
    """
    Configuration for webhook processing.

    Controls which webhooks are accepted and processed.
    """

    # Secret token for signature validation
    secret_token: str | None = None

    # Event filtering
    allowed_event_types: list[WebhookEventType] = field(
        default_factory=lambda: [WebhookEventType.MERGE_REQUEST, WebhookEventType.NOTE]
    )

    # MR action filtering
    allowed_mr_actions: list[MergeRequestAction] = field(
        default_factory=lambda: [
            MergeRequestAction.OPEN,
            MergeRequestAction.UPDATE,
            MergeRequestAction.REOPEN,
        ]
    )

    # Draft/WIP filtering
    ignore_drafts: bool = True
    ignore_wip: bool = True

    # Label filtering (empty = accept all)
    required_labels: list[str] = field(default_factory=list)
    excluded_labels: list[str] = field(default_factory=list)

    # Branch filtering (regex patterns, empty = accept all)
    allowed_source_branches: list[str] = field(default_factory=list)
    allowed_target_branches: list[str] = field(default_factory=list)
    excluded_source_branches: list[str] = field(default_factory=list)
    excluded_target_branches: list[str] = field(default_factory=list)

    # Security
    validate_signature: bool = True
    require_user_agent: bool = False
    allowed_user_agents: list[str] = field(default_factory=lambda: ["GitLab"])


class WebhookSignatureValidator:
    """
    Validates GitLab webhook signatures.

    GitLab uses simple token comparison via X-Gitlab-Token header.
    """

    def __init__(self, secret_token: str | None = None):
        """
        Initialize signature validator.

        Args:
            secret_token: Secret token configured in GitLab webhook settings
        """
        self.secret_token = secret_token
        self._logger = get_logger(f"{__name__}.WebhookSignatureValidator")

    def validate(self, headers: dict[str, str], body: bytes | str | None = None) -> bool:
        """
        Validate webhook signature.

        GitLab sends the secret token in the X-Gitlab-Token header.

        Args:
            headers: Request headers (case-insensitive)
            body: Request body (unused for GitLab, kept for API consistency)

        Returns:
            True if signature is valid, False otherwise

        Raises:
            WebhookValidationError: If validation cannot be performed
        """
        # If no secret token configured, skip validation
        if not self.secret_token:
            self._logger.warning(
                "No secret token configured, skipping signature validation",
                extra={"security_warning": True},
            )
            return True

        # Normalize headers to lowercase for case-insensitive lookup
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        # Check for X-Gitlab-Token header
        gitlab_token = normalized_headers.get("x-gitlab-token")

        if not gitlab_token:
            self._logger.error(
                "Missing X-Gitlab-Token header in webhook request",
                extra={"headers": list(normalized_headers.keys())},
            )
            raise WebhookValidationError(
                "Missing X-Gitlab-Token header",
                validation_error=None,
            )

        # GitLab uses simple string comparison
        is_valid = hmac.compare_digest(gitlab_token, self.secret_token)

        if not is_valid:
            self._logger.error(
                "Invalid webhook signature",
                extra={"expected_length": len(self.secret_token), "received_length": len(gitlab_token)},
            )
        else:
            self._logger.debug("Webhook signature validated successfully")

        return is_valid

    def generate_signature(self, body: bytes | str) -> str:
        """
        Generate a signature for testing purposes.

        For GitLab, this just returns the secret token.

        Args:
            body: Request body (unused)

        Returns:
            The secret token
        """
        if not self.secret_token:
            raise WebhookValidationError("No secret token configured")

        return self.secret_token


class WebhookEventFilter:
    """
    Filters webhook events based on configuration.

    Determines whether a webhook should be processed based on
    event type, MR state, labels, branches, etc.
    """

    def __init__(self, config: WebhookConfig):
        """
        Initialize event filter.

        Args:
            config: Webhook configuration
        """
        self.config = config
        self._logger = get_logger(f"{__name__}.WebhookEventFilter")

        # Compile branch patterns
        self._allowed_source_patterns = [
            re.compile(pattern) for pattern in config.allowed_source_branches
        ]
        self._allowed_target_patterns = [
            re.compile(pattern) for pattern in config.allowed_target_branches
        ]
        self._excluded_source_patterns = [
            re.compile(pattern) for pattern in config.excluded_source_branches
        ]
        self._excluded_target_patterns = [
            re.compile(pattern) for pattern in config.excluded_target_branches
        ]

    def should_process(
        self,
        event_type: WebhookEventType,
        payload: MergeRequestWebhookPayload | PushWebhookPayload | NoteWebhookPayload,
    ) -> tuple[bool, str | None]:
        """
        Determine if webhook should be processed.

        Args:
            event_type: Type of webhook event
            payload: Parsed webhook payload

        Returns:
            Tuple of (should_process, rejection_reason)
        """
        # Check event type
        if event_type not in self.config.allowed_event_types:
            reason = f"Event type '{event_type.value}' not in allowed types"
            self._logger.info(f"Rejecting webhook: {reason}")
            return False, reason

        # Type-specific filtering
        if event_type == WebhookEventType.MERGE_REQUEST:
            return self._filter_merge_request(payload)  # type: ignore
        elif event_type == WebhookEventType.PUSH:
            return self._filter_push(payload)  # type: ignore
        elif event_type == WebhookEventType.NOTE:
            return self._filter_note(payload)  # type: ignore

        # Unknown event type (should not reach here)
        return True, None

    def _filter_merge_request(
        self, payload: MergeRequestWebhookPayload
    ) -> tuple[bool, str | None]:
        """
        Filter merge request webhook.

        Args:
            payload: MR webhook payload

        Returns:
            Tuple of (should_process, rejection_reason)
        """
        mr = payload.object_attributes

        # Check MR action
        action = mr.action if hasattr(mr, "action") else "unknown"
        try:
            mr_action = MergeRequestAction(action)
            if mr_action not in self.config.allowed_mr_actions:
                reason = f"MR action '{action}' not in allowed actions"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason
        except ValueError:
            reason = f"Unknown MR action '{action}'"
            self._logger.warning(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
            return False, reason

        # Check draft/WIP status
        if self.config.ignore_drafts or self.config.ignore_wip:
            if mr.is_draft:
                reason = "MR is marked as draft/WIP"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason

        # Check labels
        mr_labels = set(mr.labels)
        if self.config.required_labels:
            required = set(self.config.required_labels)
            if not required.issubset(mr_labels):
                missing = required - mr_labels
                reason = f"MR missing required labels: {', '.join(missing)}"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason

        if self.config.excluded_labels:
            excluded = set(self.config.excluded_labels)
            if excluded.intersection(mr_labels):
                found = excluded.intersection(mr_labels)
                reason = f"MR has excluded labels: {', '.join(found)}"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason

        # Check branches
        source_branch = mr.source_branch
        target_branch = mr.target_branch

        # Check allowed source branches
        if self._allowed_source_patterns:
            if not any(pattern.match(source_branch) for pattern in self._allowed_source_patterns):
                reason = f"Source branch '{source_branch}' not in allowed patterns"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason

        # Check allowed target branches
        if self._allowed_target_patterns:
            if not any(pattern.match(target_branch) for pattern in self._allowed_target_patterns):
                reason = f"Target branch '{target_branch}' not in allowed patterns"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason

        # Check excluded source branches
        if self._excluded_source_patterns:
            if any(pattern.match(source_branch) for pattern in self._excluded_source_patterns):
                reason = f"Source branch '{source_branch}' matches excluded pattern"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason

        # Check excluded target branches
        if self._excluded_target_patterns:
            if any(pattern.match(target_branch) for pattern in self._excluded_target_patterns):
                reason = f"Target branch '{target_branch}' matches excluded pattern"
                self._logger.info(f"Rejecting MR webhook: {reason}", extra={"mr_iid": mr.iid})
                return False, reason

        # All checks passed
        self._logger.info(
            "MR webhook passed all filters",
            extra={
                "mr_iid": mr.iid,
                "action": action,
                "source_branch": source_branch,
                "target_branch": target_branch,
                "labels": list(mr_labels),
            },
        )
        return True, None

    def _filter_push(self, payload: PushWebhookPayload) -> tuple[bool, str | None]:
        """
        Filter push webhook.

        Args:
            payload: Push webhook payload

        Returns:
            Tuple of (should_process, rejection_reason)
        """
        branch = payload.branch_name

        # Check allowed branches
        if self._allowed_source_patterns:
            if not any(pattern.match(branch) for pattern in self._allowed_source_patterns):
                reason = f"Branch '{branch}' not in allowed patterns"
                self._logger.info(f"Rejecting push webhook: {reason}")
                return False, reason

        # Check excluded branches
        if self._excluded_source_patterns:
            if any(pattern.match(branch) for pattern in self._excluded_source_patterns):
                reason = f"Branch '{branch}' matches excluded pattern"
                self._logger.info(f"Rejecting push webhook: {reason}")
                return False, reason

        # Check for branch deletion
        if payload.is_deleted_branch:
            reason = "Push is a branch deletion"
            self._logger.info(f"Rejecting push webhook: {reason}")
            return False, reason

        # All checks passed
        self._logger.info(
            "Push webhook passed all filters",
            extra={
                "branch": branch,
                "commits_count": payload.total_commits_count,
                "is_new_branch": payload.is_new_branch,
            },
        )
        return True, None

    def _filter_note(
        self, payload: NoteWebhookPayload
    ) -> tuple[bool, str | None]:
        """
        Filter note webhook.

        Args:
            payload: Note webhook payload

        Returns:
            Tuple of (should_process, rejection_reason)
        """
        # Check if note is on a merge request
        if not payload.is_merge_request_note:
            reason = "Note is not on a merge request"
            self._logger.debug(f"Rejecting note webhook: {reason}", extra={"note_id": payload.object_attributes.id})
            return False, reason

        # Check if note is part of a discussion
        if not payload.is_discussion_note:
            reason = "Note is not part of a discussion"
            self._logger.debug(f"Rejecting note webhook: {reason}", extra={"note_id": payload.object_attributes.id})
            return False, reason

        # Check if note is resolvable
        if not payload.object_attributes.resolvable:
            reason = "Note is not resolvable"
            self._logger.debug(f"Rejecting note webhook: {reason}", extra={"note_id": payload.object_attributes.id})
            return False, reason

        # Check if note is already resolved
        if payload.object_attributes.resolved:
            reason = "Note is already resolved"
            self._logger.debug(f"Rejecting note webhook: {reason}", extra={"note_id": payload.object_attributes.id})
            return False, reason

        # Check if note body is "done" (case-insensitive)
        if payload.note_body.strip().lower() != "done":
            reason = f"Note body does not match 'done': '{payload.note_body.strip()}'"
            self._logger.debug(f"Rejecting note webhook: {reason}", extra={"note_id": payload.object_attributes.id})
            return False, reason

        # All checks passed
        self._logger.info(
            "Note webhook passed all filters",
            extra={
                "note_id": payload.object_attributes.id,
                "discussion_id": payload.discussion_id,
                "note_body": payload.note_body.strip(),
            },
        )
        return True, None


def validate_webhook(
    headers: dict[str, str],
    body: dict[str, Any],
    config: WebhookConfig,
) -> WebhookValidationResult:
    """
    Validate and parse a webhook request.

    This is the main entry point for webhook validation. It performs:
    1. Signature validation
    2. Event type detection
    3. Payload parsing and validation
    4. Event filtering

    Args:
        headers: Request headers
        body: Request body (as dictionary)
        config: Webhook configuration

    Returns:
        WebhookValidationResult with validation status and parsed payload

    Raises:
        WebhookValidationError: If validation fails critically
    """
    logger.info("Starting webhook validation")

    # Normalize headers
    normalized_headers = {k.lower(): v for k, v in headers.items()}

    # 1. Validate signature
    if config.validate_signature:
        validator = WebhookSignatureValidator(config.secret_token)
        if not validator.validate(headers):
            return WebhookValidationResult(
                is_valid=False,
                should_process=False,
                rejection_reason="Invalid webhook signature",
            )

    # 2. Check User-Agent if required
    if config.require_user_agent:
        user_agent = normalized_headers.get("user-agent", "")
        if not any(allowed in user_agent for allowed in config.allowed_user_agents):
            logger.warning(
                "Webhook rejected due to User-Agent",
                extra={"user_agent": user_agent, "allowed": config.allowed_user_agents},
            )
            return WebhookValidationResult(
                is_valid=False,
                should_process=False,
                rejection_reason=f"User-Agent '{user_agent}' not allowed",
            )

    # 3. Detect event type
    event_header = normalized_headers.get("x-gitlab-event")
    if not event_header:
        logger.error("Missing X-Gitlab-Event header")
        return WebhookValidationResult(
            is_valid=False,
            should_process=False,
            rejection_reason="Missing X-Gitlab-Event header",
        )

    try:
        event_type = WebhookEventType(event_header)
    except ValueError:
        logger.warning(f"Unknown event type: {event_header}")
        return WebhookValidationResult(
            is_valid=False,
            should_process=False,
            rejection_reason=f"Unknown event type: {event_header}",
        )

    # 4. Parse payload based on event type
    try:
        if event_type == WebhookEventType.MERGE_REQUEST:
            payload = MergeRequestWebhookPayload(**body)
        elif event_type == WebhookEventType.PUSH:
            payload = PushWebhookPayload(**body)
        elif event_type == WebhookEventType.NOTE:
            payload = NoteWebhookPayload(**body)
        else:
            logger.info(f"Event type {event_type.value} not supported for processing")
            return WebhookValidationResult(
                is_valid=True,
                event_type=event_type,
                should_process=False,
                rejection_reason=f"Event type {event_type.value} not configured for processing",
            )
    except ValidationError as e:
        logger.error(
            f"Failed to parse {event_type.value} payload",
            extra={"validation_error": str(e), "error_count": len(e.errors())},
        )
        return WebhookValidationResult(
            is_valid=False,
            event_type=event_type,
            should_process=False,
            rejection_reason=f"Invalid payload structure: {str(e)}",
        )

    # 5. Filter event
    event_filter = WebhookEventFilter(config)
    should_process, rejection_reason = event_filter.should_process(event_type, payload)

    logger.info(
        f"Webhook validation complete: should_process={should_process}",
        extra={
            "event_type": event_type.value,
            "should_process": should_process,
            "rejection_reason": rejection_reason,
        },
    )

    return WebhookValidationResult(
        is_valid=True,
        event_type=event_type,
        should_process=should_process,
        rejection_reason=rejection_reason,
        payload=payload,
    )
