# Auto-Close Discussion Feature

## Overview

The auto-close discussion feature automatically resolves/closes review discussion threads on merge requests when reviewers reply with a simple "done" command. This streamlines the review workflow by eliminating the need for manual discussion resolution.

## Feature Description

### What It Does

When a code review bot posts comments with suggestions or feedback, discussion threads are created automatically. This feature allows reviewers to close those discussions by simply replying with "done" (case-insensitive), and the bot will automatically resolve the thread.

### Workflow

```
Reviewer sees bot suggestion
         ↓
Implements suggested change
         ↓
Replies to discussion: "done"
         ↓
Bot webhook receives Note Hook event
         ↓
Bot verifies discussion was bot-created
         ↓
Bot resolves/closes the discussion
         ↓
Discussion shows as "Resolved" in GitLab UI
```

## Configuration

### Prerequisites

1. **Webhook Setup**
   - The bot server must be running and accessible
   - Webhook must be configured in GitLab project settings
   - Note Hook trigger event must be enabled

2. **Bot User Account**
   - Bot must have a valid GitLab user account
   - Bot user must have permissions to post comments on MRs
   - Bot user must have permissions to resolve discussions

3. **Environment Configuration**
   - `BOT_USERNAME` environment variable set to the bot's GitLab username
   - `GITLAB_TOKEN` must have sufficient permissions
   - `WEBHOOK_SECRET` must match GitLab webhook configuration

### Environment Variables

#### Required

| Variable | Description | Example |
|----------|-------------|---------|
| `BOT_USERNAME` | Bot's GitLab username | `review-bot` |
| `GITLAB_TOKEN` | GitLab personal access token | `glpat-xxxxxxxxxxxx` |
| `WEBHOOK_SECRET` | Secret token for webhook validation | `a1b2c3d4e5f6...` |

#### Token Permissions

The `GITLAB_TOKEN` must have these scopes:

- `api` - Full API access
- `read_api` - Read API access
- `write_repository` - Write to repositories

**Note:** The token does NOT need admin privileges. Use the minimum required permissions.

### GitLab Webhook Setup

1. Navigate to your GitLab project
2. Go to **Settings** > **Integrations** > **Webhooks**
3. Create or edit your webhook
4. Under "Trigger events", ensure **Note Hook** is checked
5. Save the webhook

### Example .env Configuration

```bash
# Discussion Auto-Close Feature
BOT_USERNAME=review-bot

# Webhook Configuration
WEBHOOK_SECRET=your_secret_token_here
WEBHOOK_ENABLED=true

# GitLab Configuration
GITLAB_TOKEN=glpat-your-token-here
GITLAB_API_URL=https://gitlab.com/api/v4
```

## Usage

### Basic Usage

When the bot posts a review comment, a discussion thread is automatically created. To close it:

1. Review the suggestion
2. Reply to the discussion thread with exactly: `done`
3. Bot automatically resolves the discussion

### Examples

#### Valid Replies (Will Resolve)

- `done` - lowercase
- `Done` - capitalized
- `DONE` - uppercase
- `  done  ` - with whitespace
- `Done\n` - with newline

#### Invalid Replies (Will NOT Resolve)

- `done!` - with punctuation
- `Done!` - with punctuation
- `I'm done` - part of longer text
- `almost done` - not standalone
- `done?` - with punctuation

### Real-World Scenarios

#### Scenario 1: Simple Suggestion

```
Bot comment:
"Consider using a list comprehension for better performance"

Reviewer action:
Replies: "done"

Result:
Discussion is automatically resolved
```

#### Scenario 2: Multi-part Review

```
Bot posts multiple comments on different parts of the code

Reviewer can reply "done" to each discussion independently

Result:
Each discussion is resolved as the reviewer confirms
```

#### Scenario 3: Partial Implementation

```
Bot suggests optimization

Reviewer partially implements and replies: "done"

Result:
Discussion is resolved (future reviews can add new discussions)
```

## Technical Details

### Implementation

The feature is implemented through:

1. **Webhook Handler** (`src/webhook/handlers.py`)
   - `handle_note_event()` - Processes Note Hook webhook events
   - Validates discussion ownership and state
   - Triggers discussion resolution

2. **GitLab Client** (`src/gitlab_client_async.py`)
   - `get_discussion()` - Fetches discussion details
   - `resolve_discussion()` - Resolves a discussion thread

3. **Webhook Models** (`src/webhook/models.py`)
   - `NoteWebhookPayload` - Represents Note Hook events
   - Validates note and discussion information

### Processing Logic

```
Receive Note Hook webhook
    ↓
Validate webhook signature
    ↓
Parse payload as NoteWebhookPayload
    ↓
Check if note is on a merge request
    ↓
Check if note is part of a discussion thread
    ↓
Check if note body == "done" (case-insensitive)
    ↓
Fetch discussion from GitLab API
    ↓
Check if discussion was created by bot user
    ↓
Check if discussion is not already resolved
    ↓
Call resolve_discussion() API
    ↓
Log result
```

### API Endpoints Used

The feature uses these GitLab API endpoints:

1. **Get Discussion Details**
   ```
   GET /projects/{project_id}/merge_requests/{mr_iid}/discussions/{discussion_id}
   ```

2. **Resolve Discussion**
   ```
   PUT /projects/{project_id}/merge_requests/{mr_iid}/discussions/{discussion_id}
   ```
   Body: `{"resolved": true}`

## Validation Requirements

The bot only resolves a discussion if **ALL** these conditions are met:

| Requirement | Check | Reason |
|-------------|-------|--------|
| Note is on MR | Noteable type == "MergeRequest" | Feature only for MRs |
| Note in discussion | `is_discussion_note` == true | Not standalone comments |
| Discussion exists | API returns discussion details | Valid discussion |
| Discussion resolvable | Discussion has `resolvable` flag | GitLab allows resolution |
| Not already resolved | `resolved` field == false | No duplicate resolution |
| Note body is "done" | `body.strip().lower() == "done"` | Exact match required |
| Discussion by bot | Discussion creator username == BOT_USERNAME | Only bot threads |

### Error Handling

If any requirement fails, the bot:

1. Logs the skip reason at INFO level
2. Returns success status (no error)
3. Does not attempt resolution

This design ensures the feature is non-disruptive and won't fail the webhook if conditions aren't met.

## Logging

### Log Entries

The feature generates these log entries:

**Successful Resolution:**
```
INFO - Processing note event
DEBUG - Processing note event
INFO - Discussion resolved successfully
```

**Skipped Due to Conditions:**
```
INFO - Processing note event
INFO - Webhook rejected by filters: ...
```

### Enabling Debug Logging

For detailed troubleshooting:

```bash
# Set environment variable
LOG_LEVEL=DEBUG

# Or in Docker
docker run -e LOG_LEVEL=DEBUG review-bot:latest

# View logs
docker logs -f review-bot | grep -i "note\|discussion"
```

## Troubleshooting

### Discussion Not Resolving

**Problem:** Replied with "done" but discussion remains unresolved

**Possible Causes:**

1. **Note Hook not enabled in webhook**
   - Check GitLab project Settings > Integrations > Webhooks
   - Ensure "Note Hook" is checked
   - Test webhook connectivity

2. **BOT_USERNAME mismatch**
   - Verify bot's actual GitLab username
   - Update BOT_USERNAME in environment
   - Restart bot server

3. **Wrong reply text**
   - Must be exactly "done" (any case, whitespace trimmed)
   - "done!" or "done." won't work
   - Reply must not include other text

4. **Discussion not bot-created**
   - Bot only resolves discussions it created
   - Check GitLab UI for discussion creator
   - Manual discussions won't resolve

5. **Discussion already resolved**
   - Already resolved discussions can't be re-resolved
   - Replying "done" has no effect
   - Check discussion status in GitLab UI

6. **Token permissions insufficient**
   - Token needs `api` and `write_repository` scopes
   - Check token permissions in GitLab

### Debugging

Enable debug logs and check for:

```bash
docker logs review-bot | grep -E "note_event|discussion|resolve"
```

Expected debug output:

```
DEBUG Processing note event
DEBUG Validating note conditions
DEBUG Retrieved discussion details
INFO Discussion resolved successfully
```

### Manual Testing

Test using GitLab API:

```bash
# Get discussion details
curl -H "Private-Token: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/123/merge_requests/45/discussions"

# Manually resolve (for testing)
curl -X PUT -H "Private-Token: $GITLAB_TOKEN" \
  -d '{"resolved": true}' \
  "https://gitlab.com/api/v4/projects/123/merge_requests/45/discussions/abc123"
```

## Performance Considerations

### Webhook Processing

- Note Hook processing is async and non-blocking
- Resolving discussions happens in background
- Webhook response is immediate (< 100ms typically)

### API Rate Limiting

- Each discussion resolution = 2 GitLab API calls (fetch + update)
- GitLab rate limit: ~1000 requests/hour
- Typical usage: minimal impact

### Scalability

- Handles multiple concurrent webhook events
- No database overhead for tracking
- Uses GitLab API as source of truth

## Security Considerations

### Bot Username Verification

The bot verifies that discussions were created by the bot user before resolving. This prevents:

- Resolving discussions created by other users
- Accidental resolution of non-bot discussions
- Unauthorized discussion closing

### Token Scopes

The GitLab token uses minimal required permissions:

- No admin access
- No sudo access
- Only `api` and `write_repository`
- Consider using project-level tokens

### Webhook Signature Validation

All webhooks are validated using:

- X-Gitlab-Token header verification
- Payload signature validation
- Hash comparison before processing

## Related Files

### Source Code

- `/home/nolood/general/review-bot/src/webhook/handlers.py` - Note event handler
- `/home/nolood/general/review-bot/src/webhook/models.py` - NoteWebhookPayload model
- `/home/nolood/general/review-bot/src/webhook/validators.py` - Event filtering
- `/home/nolood/general/review-bot/src/gitlab_client_async.py` - API client
- `/home/nolood/general/review-bot/src/app_server.py` - Webhook integration

### Documentation

- `/home/nolood/general/review-bot/docs/webhook_setup.md` - Webhook configuration
- `/home/nolood/general/review-bot/docs/usage.md` - Feature usage examples
- `/home/nolood/general/review-bot/docs/api.md` - API documentation

## FAQ

### Q: Can I use any text to close discussions?
**A:** No, only exactly "done" (case-insensitive, whitespace trimmed).

### Q: What if I accidentally reply "done" to the wrong discussion?
**A:** Make sure BOT_USERNAME is correct. Bot only resolves discussions it created.

### Q: Can the bot resolve discussions created by other users?
**A:** No, it only resolves discussions created by the bot user.

### Q: Does this work on issues?
**A:** No, only on merge request discussions.

### Q: What happens if the token doesn't have permission to resolve?
**A:** The API call fails, is logged, and webhook returns success (non-disruptive).

### Q: Can I disable this feature?
**A:** Remove the Note Hook trigger event from webhook in GitLab settings.

### Q: Is there a way to customize the trigger word?
**A:** Currently hardcoded to "done". Future versions could make it configurable.

## Future Enhancements

Potential improvements for this feature:

1. **Configurable Trigger Word**
   - Allow custom keywords instead of hardcoded "done"

2. **Resolve All Discussions**
   - Optional command to resolve all discussions at once

3. **Conditional Resolution**
   - Resolve only certain types of discussions

4. **Notification Integration**
   - Notify reviewers when discussions are resolved

5. **Metrics and Analytics**
   - Track discussion resolution rates
   - Measure review cycle times

## Examples

See `/home/nolood/general/review-bot/docs/usage.md` for workflow examples and usage patterns.

## Support

For issues or questions:

1. Check troubleshooting section above
2. Enable debug logging and review logs
3. Test webhook connectivity in GitLab
4. Verify environment configuration
