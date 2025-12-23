"""
Main webhook request handler for GitLab webhooks.

Provides comprehensive webhook processing with:
- Signature validation
- Payload parsing and validation
- Event filtering and routing
- Context extraction for code review
"""

import json
from dataclasses import dataclass
from typing import Any, Optional

from pydantic import ValidationError

from ..utils.logger import get_logger
from ..utils.exceptions import ReviewBotError
from .models import (
    WebhookEventType,
    MergeRequestWebhookPayload,
    PushWebhookPayload,
    WebhookValidationResult,
)
from .validators import (
    WebhookConfig,
    WebhookSignatureValidator,
    WebhookEventFilter,
    WebhookValidationError,
)

logger = get_logger(__name__)


class WebhookParsingError(ReviewBotError):
    """
    Raised when webhook payload parsing fails.

    This includes JSON parsing errors, schema validation failures,
    and missing required fields.
    """

    def __init__(
        self,
        message: str,
        payload_excerpt: Optional[str] = None,
        validation_errors: Optional[list[dict[str, Any]]] = None,
    ):
        """Initialize webhook parsing error."""
        details: dict[str, Any] = {}
        if payload_excerpt:
            details["payload_excerpt"] = payload_excerpt
        if validation_errors:
            details["validation_errors"] = validation_errors

        super().__init__(
            message=message,
            error_code="WEBHOOK_PARSING_ERROR",
            details=details,
        )


@dataclass
class WebhookContext:
    """
    Extracted context from webhook for code review.

    Contains all necessary information to trigger and execute
    a code review process.
    """

    # GitLab project information
    project_id: int
    project_name: str
    project_url: str

    # Merge request information
    mr_iid: int
    mr_id: int
    mr_title: str
    mr_description: Optional[str]
    mr_state: str
    mr_url: str

    # Branch information
    source_branch: str
    target_branch: str

    # Commit information
    head_sha: Optional[str]
    base_sha: Optional[str]

    # User information
    author_id: int
    author_username: str
    author_name: str

    # Additional context
    labels: list[str]
    is_draft: bool
    action: str

    def to_dict(self) -> dict[str, Any]:
        """Convert context to dictionary representation."""
        return {
            "project_id": self.project_id,
            "project_name": self.project_name,
            "project_url": self.project_url,
            "mr_iid": self.mr_iid,
            "mr_id": self.mr_id,
            "mr_title": self.mr_title,
            "mr_description": self.mr_description,
            "mr_state": self.mr_state,
            "mr_url": self.mr_url,
            "source_branch": self.source_branch,
            "target_branch": self.target_branch,
            "head_sha": self.head_sha,
            "base_sha": self.base_sha,
            "author_id": self.author_id,
            "author_username": self.author_username,
            "author_name": self.author_name,
            "labels": self.labels,
            "is_draft": self.is_draft,
            "action": self.action,
        }


class WebhookHandler:
    """
    Main handler for processing GitLab webhooks.

    Orchestrates the complete webhook processing flow:
    1. Signature validation
    2. Payload parsing
    3. Event filtering
    4. Context extraction
    """

    def __init__(self, config: WebhookConfig):
        """
        Initialize webhook handler.

        Args:
            config: Webhook processing configuration
        """
        self.config = config
        self.signature_validator = WebhookSignatureValidator(config.secret_token)
        self.event_filter = WebhookEventFilter(config)
        self._logger = get_logger(__name__)

        self._logger.info(
            "WebhookHandler initialized",
            extra={
                "validate_signature": config.validate_signature,
                "allowed_events": [e.value for e in config.allowed_event_types],
                "allowed_mr_actions": [a.value for a in config.allowed_mr_actions],
            },
        )

    async def handle_request(
        self, payload_body: bytes, headers: dict[str, str]
    ) -> WebhookValidationResult:
        """
        Handle incoming webhook request.

        Performs complete webhook processing pipeline:
        - Validates signature
        - Parses JSON payload
        - Validates payload schema
        - Filters event
        - Extracts context

        Args:
            payload_body: Raw request body bytes
            headers: Request headers

        Returns:
            WebhookValidationResult with processing status and context

        Raises:
            WebhookValidationError: If signature validation fails
            WebhookParsingError: If payload parsing fails
        """
        self._logger.info(
            "Processing webhook request",
            extra={
                "content_length": len(payload_body),
                "headers_count": len(headers),
            },
        )

        # Step 1: Validate signature
        if self.config.validate_signature:
            self._logger.debug("Validating webhook signature")
            try:
                self.signature_validator.validate(headers, payload_body)
            except WebhookValidationError as e:
                self._logger.error(
                    f"Signature validation failed: {e.message}",
                    extra={"error_code": e.error_code, "details": e.details},
                )
                raise

        # Step 2: Parse JSON payload
        self._logger.debug("Parsing JSON payload")
        try:
            payload_dict = json.loads(payload_body.decode("utf-8"))
        except json.JSONDecodeError as e:
            excerpt = payload_body[:200].decode("utf-8", errors="replace")
            self._logger.error(
                f"Failed to parse JSON payload: {str(e)}",
                extra={"excerpt": excerpt, "error": str(e)},
            )
            raise WebhookParsingError(
                f"Invalid JSON payload: {str(e)}", payload_excerpt=excerpt
            )
        except UnicodeDecodeError as e:
            self._logger.error(
                f"Failed to decode payload as UTF-8: {str(e)}",
                extra={"error": str(e)},
            )
            raise WebhookParsingError(f"Invalid UTF-8 encoding: {str(e)}")

        # Step 3: Detect event type
        event_type = self._detect_event_type(headers)
        self._logger.info(
            f"Detected webhook event type: {event_type.value if event_type else 'unknown'}"
        )

        if not event_type:
            return WebhookValidationResult(
                is_valid=False,
                should_process=False,
                rejection_reason="Could not detect event type from headers",
            )

        # Step 4: Parse and validate payload schema
        self._logger.debug(f"Validating {event_type.value} payload schema")
        try:
            payload = self._parse_payload(event_type, payload_dict)
        except ValidationError as e:
            validation_errors = [
                {"field": err["loc"], "message": err["msg"], "type": err["type"]}
                for err in e.errors()
            ]
            self._logger.error(
                f"Payload validation failed for {event_type.value}",
                extra={
                    "error_count": len(validation_errors),
                    "errors": validation_errors,
                },
            )
            raise WebhookParsingError(
                f"Invalid {event_type.value} payload schema",
                validation_errors=validation_errors,
            )

        # Step 5: Filter event
        self._logger.debug("Applying event filters")
        should_process, rejection_reason = self.event_filter.should_process(
            event_type, payload
        )

        if not should_process:
            self._logger.info(
                f"Webhook rejected by filters: {rejection_reason}",
                extra={"rejection_reason": rejection_reason},
            )
            return WebhookValidationResult(
                is_valid=True,
                event_type=event_type,
                should_process=False,
                rejection_reason=rejection_reason,
                payload=payload,
            )

        # Step 6: Success - webhook should be processed
        self._logger.info(
            "Webhook passed all validation and filters",
            extra={
                "event_type": event_type.value,
                "should_process": True,
            },
        )

        return WebhookValidationResult(
            is_valid=True,
            event_type=event_type,
            should_process=True,
            rejection_reason=None,
            payload=payload,
        )

    def extract_review_context(
        self, payload: MergeRequestWebhookPayload
    ) -> WebhookContext:
        """
        Extract review context from merge request webhook payload.

        Extracts all necessary information to initiate a code review,
        including project details, MR information, and commit data.

        Args:
            payload: Validated merge request webhook payload

        Returns:
            WebhookContext with extracted information

        Raises:
            ValueError: If required fields are missing
        """
        self._logger.debug(
            "Extracting review context from MR webhook",
            extra={
                "project_id": payload.project.id,
                "mr_iid": payload.object_attributes.iid,
            },
        )

        # Extract commit SHAs
        head_sha = None
        base_sha = None

        if payload.object_attributes.last_commit:
            head_sha = payload.object_attributes.last_commit.get("id")

        # GitLab includes oldrev in object_attributes for updates
        if hasattr(payload.object_attributes, "oldrev"):
            base_sha = payload.object_attributes.oldrev

        # Extract action (default to 'unknown' if not present)
        action = "unknown"
        if hasattr(payload.object_attributes, "action"):
            action = payload.object_attributes.action or "unknown"

        context = WebhookContext(
            # Project information
            project_id=payload.project.id,
            project_name=payload.project.name,
            project_url=payload.project.web_url,
            # MR information
            mr_iid=payload.object_attributes.iid,
            mr_id=payload.object_attributes.id,
            mr_title=payload.object_attributes.title,
            mr_description=payload.object_attributes.description,
            mr_state=payload.object_attributes.state,
            mr_url=payload.object_attributes.url,
            # Branch information
            source_branch=payload.object_attributes.source_branch,
            target_branch=payload.object_attributes.target_branch,
            # Commit information
            head_sha=head_sha,
            base_sha=base_sha,
            # User information
            author_id=payload.user.id,
            author_username=payload.user.username,
            author_name=payload.user.name,
            # Additional context
            labels=payload.object_attributes.labels,
            is_draft=payload.object_attributes.is_draft,
            action=action,
        )

        self._logger.info(
            "Review context extracted successfully",
            extra={
                "project_id": context.project_id,
                "mr_iid": context.mr_iid,
                "source_branch": context.source_branch,
                "target_branch": context.target_branch,
                "action": context.action,
                "labels_count": len(context.labels),
            },
        )

        return context

    def _detect_event_type(self, headers: dict[str, str]) -> Optional[WebhookEventType]:
        """
        Detect webhook event type from headers.

        GitLab sends the event type in the X-Gitlab-Event header.

        Args:
            headers: Request headers

        Returns:
            WebhookEventType if detected, None otherwise
        """
        # Normalize headers to lowercase
        normalized_headers = {k.lower(): v for k, v in headers.items()}

        # Get event type from X-Gitlab-Event header
        event_header = normalized_headers.get("x-gitlab-event")

        if not event_header:
            self._logger.warning(
                "Missing X-Gitlab-Event header",
                extra={"headers": list(normalized_headers.keys())},
            )
            return None

        try:
            return WebhookEventType(event_header)
        except ValueError:
            self._logger.warning(
                f"Unknown event type in X-Gitlab-Event header: {event_header}",
                extra={"event_header": event_header},
            )
            return None

    def _parse_payload(
        self, event_type: WebhookEventType, payload_dict: dict[str, Any]
    ) -> MergeRequestWebhookPayload | PushWebhookPayload:
        """
        Parse webhook payload based on event type.

        Args:
            event_type: Detected event type
            payload_dict: Parsed JSON payload

        Returns:
            Validated Pydantic payload model

        Raises:
            ValidationError: If payload doesn't match schema
            ValueError: If event type is not supported
        """
        if event_type == WebhookEventType.MERGE_REQUEST:
            return MergeRequestWebhookPayload(**payload_dict)
        elif event_type == WebhookEventType.PUSH:
            return PushWebhookPayload(**payload_dict)
        else:
            raise ValueError(f"Unsupported event type for parsing: {event_type.value}")
