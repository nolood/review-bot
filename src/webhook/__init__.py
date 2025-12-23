"""
Webhook handling infrastructure for GitLab webhooks.

This package provides models, validation, and signature verification
for processing GitLab webhook events.

Main exports:
    - WebhookHandler: Main handler for processing webhooks
    - WebhookConfig: Configuration for webhook processing
    - WebhookEventType: Enum for webhook event types
    - MergeRequestWebhookPayload: Pydantic model for MR webhooks
    - PushWebhookPayload: Pydantic model for push webhooks
"""

from .models import (
    WebhookEventType,
    MergeRequestAction,
    GitLabUser,
    GitLabProject,
    GitLabMergeRequest,
    MergeRequestChanges,
    MergeRequestWebhookPayload,
    PushCommit,
    PushWebhookPayload,
    WebhookValidationResult,
)
from .validators import (
    WebhookConfig,
    WebhookSignatureValidator,
    WebhookEventFilter,
    WebhookValidationError,
)
from .handlers import (
    WebhookHandler,
    WebhookContext,
    WebhookParsingError,
)

__all__ = [
    # Enums
    "WebhookEventType",
    "MergeRequestAction",
    # Models
    "GitLabUser",
    "GitLabProject",
    "GitLabMergeRequest",
    "MergeRequestChanges",
    "MergeRequestWebhookPayload",
    "PushCommit",
    "PushWebhookPayload",
    "WebhookValidationResult",
    # Validators
    "WebhookConfig",
    "WebhookSignatureValidator",
    "WebhookEventFilter",
    "WebhookValidationError",
    # Handlers
    "WebhookHandler",
    "WebhookContext",
    "WebhookParsingError",
]
