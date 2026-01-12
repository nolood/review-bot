# GitLab Webhook Integration Setup

## Overview

The GLM Code Review Bot supports GitLab webhooks as an alternative to CI/CD pipeline integration. This allows the bot to automatically review merge requests in real-time as soon as they are created or updated, without requiring a CI/CD pipeline job.

### Benefits Over CI/CD Approach

- **Real-time Processing**: Reviews start immediately when webhooks are triggered, not on pipeline run
- **Lower Latency**: No queue waiting time compared to CI/CD job scheduling
- **Always Available**: Webhooks work independently of CI/CD pipeline configuration
- **Simpler Setup**: Minimal configuration in your project after server deployment
- **Direct Feedback**: Comments appear immediately without pipeline overhead
- **Cost Effective**: Reduces CI/CD pipeline resource usage

### Architecture

The webhook integration consists of:

1. **GitLab Webhook Configuration**: Registers webhook in your GitLab project
2. **Server Endpoint**: HTTP POST endpoint that receives webhook events
3. **Payload Validation**: Signature verification and payload parsing
4. **Event Filtering**: Selective processing based on event type and merge request state
5. **Background Processing**: Async task processing with concurrent review handling
6. **Comment Management**: Deduplication and cleanup of previous comments

## GitLab Webhook Configuration

### Step 1: Deploy the Review Bot Server

First, ensure the review bot server is running and accessible. See the [Deployment Guide](deployment.md) for details on running the server.

Your server must be accessible from the public internet (or your GitLab instance if self-hosted). Example URLs:
- Public deployment: `https://your-review-bot.example.com`
- Internal deployment: `https://review-bot.internal.example.com`
- Cloud deployment: `https://api.your-company.com/review-bot`

### Step 2: Access GitLab Project Webhooks

1. Go to your GitLab project
2. Navigate to **Settings** > **Integrations** > **Webhooks**
3. Click **Add webhook**

### Step 3: Configure Webhook URL

In the webhook configuration form, enter:

**URL:** `https://your-bot-domain/webhook/gitlab`

Replace `your-bot-domain` with your actual server address.

Examples:
- `https://review-bot.mycompany.com/webhook/gitlab`
- `https://api.example.com:8000/webhook/gitlab`
- `https://localhost:8000/webhook/gitlab` (for local testing)

### Step 4: Set Secret Token

1. Generate a secure secret token (minimum 32 characters recommended):
   ```bash
   openssl rand -hex 32
   # Example output: a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
   ```

2. Enter the token in the **Secret token** field in GitLab webhook settings

3. Store this token in your bot server's environment variables as `WEBHOOK_SECRET`

### Step 5: Select Trigger Events

Select which events should trigger the webhook:

**Recommended Configuration:**
- [x] **Merge request events** (primary)
- [x] **Note Hook events** (for auto-closing discussions)
- [x] **Push events** (optional, for push-based reviews)

**Merge Request Events Details:**
- The webhook triggers on MR actions: open, update, reopen
- Draft/WIP merge requests are automatically skipped (configurable)
- Each trigger sends the complete MR state to the bot

**Note Hook Events Details:**
- The webhook triggers when someone replies to a discussion thread
- Used to automatically close/resolve review discussions
- Triggered for comments on merge requests and inline code comments

### Step 6: Webhook Options

Configure additional webhook settings:

- **SSL verification**: Enable (recommended for production)
  - Disable only for self-signed certificates in development
- **Push events**: Keep enabled if you want to review on direct pushes
- **Merge request events**: Must be enabled
- **Comments**: Disabled (bot doesn't need to receive comment notifications)

### Step 7: Save the Webhook

Click **Add webhook** to save the configuration.

### Step 8: Test the Connection

GitLab provides a test button for webhooks:

1. Go to your webhook configuration (Settings > Integrations > Webhooks)
2. Click the webhook entry to expand it
3. Scroll to "Recent deliveries"
4. Click the test button or trigger a test event

You should see a successful response (HTTP 200 or 202).

## Environment Variables

### Webhook Configuration Variables

Complete list of webhook-related environment variables:

```bash
# Webhook Server Configuration
WEBHOOK_ENABLED=true                          # Enable webhook server (default: true)
WEBHOOK_SECRET=your_secret_token_here         # Secret token for signature validation
WEBHOOK_HOST=0.0.0.0                          # Webhook server host (default: 0.0.0.0)
WEBHOOK_PORT=8000                             # Webhook server port (default: 8000)

# Webhook Event Filtering
WEBHOOK_TRIGGER_ACTIONS=open,update,reopen   # MR actions that trigger review
WEBHOOK_SKIP_DRAFT=true                       # Skip draft/WIP merge requests (default: true)
WEBHOOK_SKIP_WIP=true                         # Skip work-in-progress merge requests (default: true)

# Webhook Authentication
WEBHOOK_VALIDATE_SIGNATURE=true               # Validate webhook signature (default: true)
WEBHOOK_TIMEOUT_SECONDS=30                    # Webhook request timeout (default: 30)

# Discussion Auto-Close Configuration
BOT_USERNAME=review-bot                       # Bot username for discussion ownership check (default: "review-bot")

# Deduplication Configuration
DEDUPLICATION_STRATEGY=DELETE_SUMMARY_ONLY   # Comment deduplication strategy
DEDUPLICATION_ENABLED=true                    # Enable deduplication (default: true)

# Background Processing
MAX_CONCURRENT_REVIEWS=3                      # Max concurrent review tasks (default: 3)
REVIEW_TIMEOUT_SECONDS=300                    # Review processing timeout (default: 300)
```

### Core Configuration Variables

These variables must also be set for webhook integration to work:

```bash
# GitLab Configuration
GITLAB_TOKEN=your_gitlab_personal_access_token
GITLAB_API_URL=https://gitlab.com/api/v4    # or your self-hosted URL

# GLM Configuration
GLM_API_KEY=your_glm_api_key
GLM_API_URL=https://api.z.ai/api/paas/v4/chat/completions

# Processing Configuration
MAX_DIFF_SIZE=50000                          # Max diff size to process
MAX_FILES_PER_COMMENT=10                     # Max files per comment block
ENABLE_INLINE_COMMENTS=true                  # Enable inline code comments

# Review Configuration
ENABLE_SECURITY_REVIEW=true                  # Enable security checks
ENABLE_PERFORMANCE_REVIEW=true               # Enable performance analysis
MIN_SEVERITY_LEVEL=low                       # Minimum issue severity to report

# Server Configuration
SERVER_HOST=0.0.0.0                          # Server bind address
SERVER_PORT=8000                             # Server port
LOG_LEVEL=INFO                               # Logging level
```

### Environment Variable Descriptions

| Variable | Type | Default | Description |
|----------|------|---------|-------------|
| `WEBHOOK_ENABLED` | boolean | `true` | Enable/disable webhook endpoint |
| `WEBHOOK_SECRET` | string | required | Secret token for GitLab signature validation |
| `WEBHOOK_VALIDATE_SIGNATURE` | boolean | `true` | Validate X-Gitlab-Token header |
| `WEBHOOK_SKIP_DRAFT` | boolean | `true` | Automatically skip draft merge requests |
| `WEBHOOK_SKIP_WIP` | boolean | `true` | Automatically skip WIP merge requests |
| `WEBHOOK_TRIGGER_ACTIONS` | string | `open,update,reopen` | Comma-separated list of MR actions to review |
| `WEBHOOK_TIMEOUT_SECONDS` | integer | `30` | How long to wait for webhook processing |
| `BOT_USERNAME` | string | `review-bot` | Bot username to check for discussion thread ownership |
| `DEDUPLICATION_STRATEGY` | enum | `DELETE_SUMMARY_ONLY` | Strategy for handling duplicate comments |
| `MAX_CONCURRENT_REVIEWS` | integer | `3` | Maximum parallel reviews to process |
| `REVIEW_TIMEOUT_SECONDS` | integer | `300` | Maximum time for a single review |

### Example .env File

```bash
# Webhook Configuration
WEBHOOK_ENABLED=true
WEBHOOK_SECRET=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6
WEBHOOK_VALIDATE_SIGNATURE=true
WEBHOOK_SKIP_DRAFT=true
WEBHOOK_SKIP_WIP=true
WEBHOOK_TRIGGER_ACTIONS=open,update,reopen

# Discussion Auto-Close Configuration
# Set this to match your bot's GitLab username
BOT_USERNAME=review-bot

# GitLab Configuration
GITLAB_TOKEN=glpat-xxxxxxxxxxxxxxxxxxxx
GITLAB_API_URL=https://gitlab.com/api/v4

# GLM Configuration
GLM_API_KEY=your_glm_api_key_here
GLM_API_URL=https://api.z.ai/api/paas/v4/chat/completions

# Processing Configuration
MAX_DIFF_SIZE=50000
MAX_FILES_PER_COMMENT=10
ENABLE_INLINE_COMMENTS=true

# Review Configuration
ENABLE_SECURITY_REVIEW=true
ENABLE_PERFORMANCE_REVIEW=true
MIN_SEVERITY_LEVEL=low

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO
MONITORING_ENABLED=true
MONITORING_PORT=8080
MAX_CONCURRENT_REVIEWS=3
REVIEW_TIMEOUT_SECONDS=300
```

## Deduplication Strategies

Deduplication determines how the bot handles comments when processing the same merge request multiple times. This is important for preventing comment spam on frequently updated merge requests.

### DELETE_ALL

**Strategy:** Delete all previous bot comments before posting new ones

```
First update:
  - Bot posts review comments

Second update (new code changes):
  - Bot deletes ALL previous comments
  - Bot posts new review comments
  - Result: Only latest review visible
```

**When to use:**
- Merge requests with frequent updates
- When you want only the latest review visible
- High-activity projects where comment clutter is a concern
- Space-limited discussions

**Pros:**
- Clean merge request discussion history
- No duplicate comments accumulate
- Easy to see current review state

**Cons:**
- Lose historical review comments
- Can't track review evolution
- Comments on resolved items disappear

### DELETE_SUMMARY_ONLY

**Strategy:** Delete only summary/general comments, keep inline code-specific comments

```
First update:
  - Bot posts summary comment
  - Bot posts inline comments on specific lines

Second update (new changes):
  - Bot deletes summary comment only
  - Bot keeps all inline comments
  - Bot posts new summary comment
  - Bot may post new inline comments
```

**When to use:**
- Most common use case (default)
- When you want to keep code-specific feedback
- Iterative development with localized changes
- Balanced history retention

**Pros:**
- Clean summary section
- Preserves specific code feedback
- Good balance between clarity and history
- Most helpful for iterative reviews

**Cons:**
- May accumulate outdated inline comments
- More complex processing

**Recommended:** This is the default and recommended strategy for most projects.

### KEEP_ALL

**Strategy:** Keep all previous comments, post new ones without deletion

```
First update:
  - Bot posts review comments

Second update:
  - Bot keeps all previous comments
  - Bot posts new review comments
  - Result: Both visible, potentially duplicative
```

**When to use:**
- Archival/compliance requirements
- Need complete history of reviews
- Low-volume merge requests
- Projects with review tracking requirements

**Pros:**
- Complete audit trail of all reviews
- Can track how feedback evolved
- No data loss

**Cons:**
- Comment clutter increases
- Hard to find current feedback
- Merge request discussions become verbose

### DELETE_OUTDATED

**Strategy:** Delete comments from previous commits, keep current commit comments

```
First update (commit abc123):
  - Bot posts comments tagged with commit abc123

Second update (new commit def456):
  - Bot deletes comments from commit abc123
  - Bot keeps comments from commit def456
  - Bot posts new comments for any changed files
```

**When to use:**
- Detailed commit-level tracking
- Amend-heavy workflows
- When you care about commit history alignment
- Projects with strict review processes

**Pros:**
- Comments aligned with commits
- Clear which review addresses which commit
- Good for audit trails

**Cons:**
- Requires commit SHA tracking
- More complex logic
- Still may accumulate comments

## Docker Deployment

### Running the Bot Server

The bot server runs as a long-lived process that listens for webhook events.

#### Docker Run

```bash
docker run -d \
  --name review-bot \
  -p 8000:8000 \
  -p 8080:8080 \
  -e GITLAB_TOKEN="your_token" \
  -e GLM_API_KEY="your_key" \
  -e WEBHOOK_ENABLED="true" \
  -e WEBHOOK_SECRET="your_secret" \
  -v /opt/review-bot/data:/data \
  review-bot:latest
```

#### Docker Compose

```yaml
version: '3.8'

services:
  review-bot:
    image: review-bot:latest
    container_name: review-bot
    restart: unless-stopped
    ports:
      - "8000:8000"
      - "8080:8080"
    environment:
      # GitLab Configuration
      GITLAB_TOKEN: ${GITLAB_TOKEN}
      GITLAB_API_URL: https://gitlab.com/api/v4

      # GLM Configuration
      GLM_API_KEY: ${GLM_API_KEY}
      GLM_API_URL: https://api.z.ai/api/paas/v4/chat/completions

      # Webhook Configuration
      WEBHOOK_ENABLED: "true"
      WEBHOOK_SECRET: ${WEBHOOK_SECRET}
      WEBHOOK_VALIDATE_SIGNATURE: "true"
      WEBHOOK_SKIP_DRAFT: "true"
      WEBHOOK_SKIP_WIP: "true"

      # Server Configuration
      SERVER_HOST: "0.0.0.0"
      SERVER_PORT: "8000"
      LOG_LEVEL: "INFO"

      # Processing Configuration
      MAX_CONCURRENT_REVIEWS: "3"
      REVIEW_TIMEOUT_SECONDS: "300"

      # Deduplication
      DEDUPLICATION_STRATEGY: "DELETE_SUMMARY_ONLY"
      DEDUPLICATION_ENABLED: "true"

    volumes:
      # Optional: Mount volume for persistent commit tracking
      - review-bot-data:/data

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

volumes:
  review-bot-data:
    driver: local
```

#### Docker Build

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY .env.example ./.env.example

# Create data directory for persistent storage
RUN mkdir -p /data

# Expose ports
EXPOSE 8000 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run server
CMD ["python", "-m", "src.app_server", "--host", "0.0.0.0", "--port", "8000"]
```

### Port Configuration

The bot server requires two ports:

| Port | Service | Purpose | Required |
|------|---------|---------|----------|
| 8000 | Main Server | Receive webhooks, API requests | Yes |
| 8080 | Monitoring | Health checks, metrics | Optional |

Configure ports via environment variables:
```bash
SERVER_PORT=8000              # Main server port
MONITORING_PORT=8080          # Monitoring port (set to 0 to disable)
```

### Data Persistence

The bot can maintain persistent state for:

- **Commit Tracking**: Track reviewed commits to avoid duplicate reviews
- **Comment History**: Maintain comment tracking for deduplication
- **Task History**: Keep historical records of processed reviews

Mount a volume to `/data` to persist this information:

```bash
docker run -v /opt/review-bot/data:/data review-bot:latest
```

Optional but recommended for production deployments.

## Automatic Discussion Resolution

The bot includes an automatic discussion resolution feature that closes/resolves review threads based on simple commands.

### How It Works

When the bot posts review comments with suggestions or feedback, reviewers can reply with "done" to automatically resolve that discussion thread. This workflow:

1. Bot posts review comments on a merge request
2. Discussion thread is created automatically by GitLab
3. Reviewer replies to the discussion with exactly `done` (case-insensitive)
4. Bot receives the Note Hook webhook event
5. Bot verifies the discussion was created by the bot
6. Bot automatically resolves/closes the discussion thread

### Configuration

Enable automatic discussion resolution by ensuring:

1. **Note Hook events are enabled** in your GitLab webhook settings
2. **BOT_USERNAME is set correctly** to match your bot's GitLab username

```bash
# In your .env file
BOT_USERNAME=review-bot
```

If your bot user is named something different (e.g., "glm-bot", "code-reviewer"), update the BOT_USERNAME environment variable accordingly.

### Usage Example

```
1. Bot posts review comment:
   "Consider using a list comprehension here for better performance"

   - A discussion thread is automatically created

2. Reviewer reviews the suggestion and replies:
   "done"

3. Bot webhook processes the reply:
   - Detects "done" in the note
   - Confirms discussion was created by the bot
   - Resolves the discussion thread

4. Discussion shows as "Resolved" in GitLab UI
```

### Discussion Resolution Requirements

The bot will only resolve a discussion if ALL the following conditions are met:

- The note is on a **merge request** (not an issue)
- The note is part of a **discussion thread** (not a standalone comment)
- The discussion thread **exists and is resolvable**
- The discussion thread is **not already resolved**
- The note body is exactly **"done"** (case-insensitive, whitespace trimmed)
- The discussion thread was **created by the bot user** (matched against BOT_USERNAME)

If any condition fails, the bot skips the discussion without attempting resolution.

### Webhook Requirements for Auto-Close Feature

Ensure your GitLab webhook is configured to receive Note Hook events:

1. Go to **Settings** > **Integrations** > **Webhooks** in your GitLab project
2. Edit your webhook and scroll to "Trigger events"
3. Check the **Note Hook** checkbox
4. Save the webhook

This allows the bot to receive notifications when someone replies to discussion threads.

## Testing the Integration

### Test 1: Webhook URL Accessibility

Verify your webhook URL is reachable:

```bash
# From outside your network, test if webhook endpoint is accessible
curl -X GET https://your-bot-domain/webhook/gitlab

# Should return 404 or 405 (since GET is not supported for webhooks)
# Any other error means the endpoint is not accessible
```

### Test 2: Signature Validation

Create a test webhook event with proper signature:

```bash
# Generate signature token
WEBHOOK_SECRET="your_secret_token"
PAYLOAD='{"project": {"id": 123}}'

# Calculate signature (GitLab uses simple token matching)
SIGNATURE=$(echo -n "$PAYLOAD" | openssl dgst -sha256 -mac HMAC -macopt "key=$WEBHOOK_SECRET" | cut -d' ' -f2)

# Send test request
curl -X POST https://your-bot-domain/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Event: Merge Request Hook" \
  -H "X-Gitlab-Token: $WEBHOOK_SECRET" \
  -d "$PAYLOAD"
```

### Test 3: GitLab Test Delivery

Use GitLab's built-in webhook testing:

1. Go to **Settings** > **Integrations** > **Webhooks**
2. Click on your webhook
3. Scroll to "Recent deliveries"
4. Click the test event type button (e.g., "Push events", "Merge request events")
5. Check the response status and body

Expected response:
- Status: 200 or 202 (Accepted)
- Headers should include timestamps
- Body should indicate webhook was processed

### Test 4: Real Merge Request

Trigger an actual webhook by creating/updating a merge request:

1. Create a test branch
2. Commit some code
3. Create a merge request
4. GitLab automatically sends webhook to your endpoint
5. Check bot server logs for processing

### Test 5: Verify Logs

Check bot server logs to verify webhook was processed:

```bash
# View real-time logs
docker logs -f review-bot

# Look for entries like:
# INFO - Processing webhook request
# INFO - Detected webhook event type: Merge Request Hook
# INFO - Review context extracted successfully
# INFO - Starting review processing
```

### Test 6: Check GitLab Recent Deliveries

In GitLab webhook settings, view recent deliveries:

1. **Settings** > **Integrations** > **Webhooks**
2. Click your webhook
3. Scroll down to "Recent deliveries"
4. Click on delivery entries to see:
   - Request body sent to your server
   - Response status and body
   - Response time
   - Timestamp

This is helpful for debugging signature or payload issues.

### Test 7: Test Auto-Close Discussion Feature

To test the automatic discussion resolution feature:

1. **Create a test merge request** in your GitLab project
2. **Wait for the bot to post review comments** on the MR
3. **Reply to a discussion thread** with exactly "done" (any case)
4. **Check the discussion status** - it should become resolved
5. **View the bot server logs** for confirmation:
   ```bash
   docker logs -f review-bot | grep -i "discussion\|resolved"
   ```

Expected log entries:
```
INFO - Processing note event
DEBUG - Processing note event
INFO - Discussion resolved successfully
```

Common test scenarios:
- Reply "done" to a review suggestion (should resolve)
- Reply "Done" in uppercase (should resolve - case-insensitive)
- Reply with whitespace "  done  " (should resolve - whitespace trimmed)
- Reply "done" to a non-bot discussion (should skip - not bot-created)
- Reply "not done" (should skip - doesn't match exactly "done")

## Troubleshooting

### Common Issues and Solutions

#### 1. Webhook Not Being Triggered

**Symptom:** MR created/updated but no webhook request received

**Solutions:**
- Verify webhook URL is correct and accessible
  ```bash
  curl -v https://your-bot-domain/webhook/gitlab
  ```
- Check that "Merge request events" is enabled in webhook settings
- Verify GitLab can reach your server (not blocked by firewall)
- Check GitLab recent deliveries for any failed attempts
- Ensure WEBHOOK_ENABLED is true in environment

#### 2. Invalid Signature Error

**Symptom:** "Invalid webhook signature" error in logs

**Solutions:**
- Verify WEBHOOK_SECRET matches the token in GitLab webhook settings
- Check for extra spaces or encoding issues in the secret
- Regenerate the secret:
  ```bash
  openssl rand -hex 32
  ```
- Update both GitLab webhook settings and bot environment variable
- Restart the bot server after changing the secret

#### 3. Merge Request Not Reviewed

**Symptom:** Webhook received but no review comments posted

**Solutions:**
- Check if MR is being filtered (draft/WIP):
  ```bash
  # If WEBHOOK_SKIP_DRAFT=true, draft MRs are skipped
  # If WEBHOOK_SKIP_WIP=true, WIP MRs are skipped
  ```
- Verify WEBHOOK_TRIGGER_ACTIONS includes the MR action (open, update, reopen)
- Check GITLAB_TOKEN has correct permissions:
  ```bash
  # Token needs: api, read_api, write_repository
  ```
- Verify GLM_API_KEY is valid and has available quota
- Check server logs for processing errors

#### 4. Comments Not Appearing

**Symptom:** Webhook processed successfully but no comments visible on MR

**Solutions:**
- Check GitLab API permissions for bot user/token
  - Token needs: api, read_api, write_repository
- Verify ENABLE_INLINE_COMMENTS is true (if expecting inline comments)
- Check for deduplication removing comments
  - Review DEDUPLICATION_STRATEGY setting
- Look for GitLab API errors in logs:
  ```bash
  docker logs review-bot | grep -i "error\|failed"
  ```
- Verify MAX_DIFF_SIZE is large enough for your changes
  - Default: 50000 bytes

#### 5. High Number of Duplicate Comments

**Symptom:** Many versions of the same comment appearing on MR

**Solutions:**
- Change DEDUPLICATION_STRATEGY to DELETE_SUMMARY_ONLY (recommended)
- Or set to DELETE_ALL if you want only latest comments
- Ensure DEDUPLICATION_ENABLED is true
- Check that comment tracking is persisted (volume mount configured)

#### 6. Webhook Timeouts

**Symptom:** 504 or timeout errors in GitLab delivery logs

**Solutions:**
- Increase WEBHOOK_TIMEOUT_SECONDS in environment
- Check if reviews are taking too long (REVIEW_TIMEOUT_SECONDS)
- Reduce MAX_CONCURRENT_REVIEWS if server is overloaded
- Check server resource usage:
  ```bash
  docker stats review-bot
  ```
- Monitor glm-api.z.ai latency (may be experiencing issues)

#### 7. Server Crashes on Startup

**Symptom:** Container exits immediately after starting

**Solutions:**
- Check logs for missing dependencies:
  ```bash
  docker logs review-bot
  ```
- Verify all required environment variables are set:
  ```bash
  docker inspect review-bot | grep Env
  ```
- Check Python version compatibility (requires 3.9+)
- Verify dependencies are installed:
  ```bash
  pip install fastapi uvicorn pydantic requests
  ```

#### 8. Authentication Failures

**Symptom:** 401 or 403 errors when accessing GitLab API

**Solutions:**
- Verify GITLAB_TOKEN is correct and not expired:
  ```bash
  # Test token validity
  curl -H "Private-Token: $GITLAB_TOKEN" \
    https://gitlab.com/api/v4/user
  ```
- Check token permissions (needs: api, read_api, write_repository)
- For self-hosted GitLab, verify GITLAB_API_URL is correct
- Ensure token hasn't been revoked

### Debug Logging

Enable debug logging for detailed troubleshooting:

```bash
# In environment variables
LOG_LEVEL=DEBUG

# Or in Docker
docker run -e LOG_LEVEL=DEBUG review-bot:latest

# View debug logs
docker logs -f review-bot
```

Debug logs will show:
- Webhook signature validation steps
- Payload parsing details
- Event filtering decisions
- API call details
- Processing progress

### Webhook Delivery Inspection

GitLab provides detailed webhook delivery information:

1. **Settings** > **Integrations** > **Webhooks**
2. Click on your webhook
3. Scroll to "Recent deliveries"
4. Click a delivery entry to expand

You'll see:
- **Request headers** sent to your server
- **Request body** (full webhook payload)
- **Response status code** from your server
- **Response headers** from your server
- **Response body** returned to GitLab

This is invaluable for debugging payload format issues.

### Manual Testing

Send a test webhook request:

```bash
# Create test merge request payload
cat > mr_webhook.json << 'EOF'
{
  "object_kind": "merge_request",
  "event_type": "merge_request",
  "user": {
    "id": 1,
    "username": "admin",
    "name": "Administrator",
    "email": "admin@example.com"
  },
  "project": {
    "id": 1,
    "name": "Example Project",
    "web_url": "https://example.com/my-group/my-project"
  },
  "object_attributes": {
    "id": 1,
    "iid": 1,
    "title": "Test MR",
    "description": "Test merge request",
    "state": "opened",
    "source_branch": "feature-branch",
    "target_branch": "main",
    "url": "https://example.com/my-group/my-project/-/merge_requests/1",
    "action": "open"
  }
}
EOF

# Send to your webhook endpoint
curl -X POST https://your-bot-domain/webhook/gitlab \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Event: Merge Request Hook" \
  -H "X-Gitlab-Token: your_webhook_secret" \
  -d @mr_webhook.json
```

### Checking Recent Webhook Deliveries

GitLab maintains a log of webhook deliveries:

```bash
# Via GitLab API
curl -H "Private-Token: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/PROJECT_ID/hooks/HOOK_ID/events"

# Shows all recent webhook attempts and their responses
```

### Troubleshooting Auto-Close Discussion Feature

#### Issue: Discussion Not Resolving When Replying "done"

**Symptom:** Reply with "done" but discussion remains unresolved

**Possible Causes and Solutions:**

1. **Note Hook events not enabled**
   - Verify in GitLab: Settings > Integrations > Webhooks
   - Ensure "Note Hook" is checked in trigger events
   - Test the webhook connection

2. **BOT_USERNAME doesn't match bot's actual username**
   ```bash
   # Check your bot's GitLab username
   # Then update .env file
   BOT_USERNAME=actual-bot-username
   # Restart the bot server
   docker restart review-bot
   ```

3. **Reply text doesn't match exactly "done"**
   - Must be exactly "done" (case-insensitive)
   - Whitespace is trimmed automatically
   - "done!" or "done." will NOT match
   - Must be standalone, not part of longer text

4. **Discussion not created by the bot**
   - Bot only resolves discussions it created
   - If manually created discussion, bot won't resolve it
   - Check GitLab UI to see who created the discussion

5. **Discussion already resolved**
   - If discussion is already resolved, bot skips it
   - Replying "done" won't have effect on resolved discussions

6. **GITLAB_TOKEN lacks required permissions**
   - Token needs `api` and `write_repository` scopes
   - Test token permissions:
   ```bash
   curl -H "Private-Token: $GITLAB_TOKEN" \
     https://gitlab.com/api/v4/user
   ```

#### Checking Discussion Resolution Logs

Enable debug logging to see discussion processing:

```bash
# Set log level to DEBUG
docker run -e LOG_LEVEL=DEBUG review-bot:latest

# View logs with filtering
docker logs -f review-bot | grep -i "note\|discussion\|resolve"
```

Look for entries like:
```
DEBUG - Processing note event
DEBUG - Discussion ID found in payload
DEBUG - Retrieved discussion details
INFO - Discussion resolved successfully
```

#### Manual Discussion Resolution Test

Create a test using the GitLab API:

```bash
# 1. Get a discussion ID from an MR
PROJECT_ID=123
MR_IID=45
curl -H "Private-Token: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/merge_requests/$MR_IID/discussions" | jq

# 2. Manually resolve a discussion (for testing)
DISCUSSION_ID="abc123def456"
curl -X PUT -H "Private-Token: $GITLAB_TOKEN" \
  "https://gitlab.com/api/v4/projects/$PROJECT_ID/merge_requests/$MR_IID/discussions/$DISCUSSION_ID" \
  -d '{"resolved": true}'
```

## Security Considerations

### Secret Token Management

- **Generate Strong Tokens**: Use at least 32 random bytes
  ```bash
  openssl rand -hex 32  # 64 character hex string
  ```
- **Rotate Regularly**: Change token every 90 days
- **Never Log**: Don't include secret in debug output
- **Separate Storage**: Keep token in secure secret manager (not version control)

### HTTPS/TLS Requirements

- **Always Use HTTPS**: Required for production
- **Valid Certificate**: Use trusted CA certificates
- **For Self-Signed**: Disable SSL verification only in development
  - Not recommended for production

### API Token Permissions

The GITLAB_TOKEN needs these scopes:
- `api` - Full API access
- `read_api` - Read API
- `write_repository` - Write to repositories

Do NOT grant unnecessary permissions:
- Avoid `admin` scope
- Avoid `sudo` access
- Use project-level tokens when possible

### Rate Limiting

Configure rate limits to prevent abuse:

```bash
# Max concurrent reviews limits resource usage
MAX_CONCURRENT_REVIEWS=3

# Review timeout prevents hanging requests
REVIEW_TIMEOUT_SECONDS=300

# Webhook timeout prevents slow-hash attacks
WEBHOOK_TIMEOUT_SECONDS=30
```

### Network Security

- **Firewall**: Restrict webhook endpoint to trusted sources if possible
- **VPN**: Consider VPN tunnel for self-hosted instances
- **Load Balancer**: Use TLS termination at load balancer
- **WAF**: Consider Web Application Firewall for DDoS protection

## Files Related to Webhook Integration

Key source files implementing webhook functionality:

- `/home/nolood/general/review-bot/src/app_server.py` - Main Flask/FastAPI server with webhook endpoint
- `/home/nolood/general/review-bot/src/webhook/handlers.py` - Webhook request handling and payload parsing
- `/home/nolood/general/review-bot/src/webhook/validators.py` - Signature validation and event filtering
- `/home/nolood/general/review-bot/src/webhook/models.py` - Pydantic models for webhook payloads
- `/home/nolood/general/review-bot/src/deduplication/comment_tracker.py` - Comment deduplication logic
- `/home/nolood/general/review-bot/src/deduplication/commit_tracker.py` - Commit tracking for avoiding re-reviews

## Next Steps

1. **Deploy the Server** - See [Deployment Guide](deployment.md)
2. **Configure Environment** - Set all required environment variables
3. **Set Up Webhook** - Follow the GitLab webhook configuration steps above
4. **Test Integration** - Run the testing steps to verify everything works
5. **Monitor Deployments** - Check logs and metrics using health endpoints

## Additional Resources

- [GitLab Webhook Documentation](https://docs.gitlab.com/ee/user/project/integrations/webhooks.html)
- [Deployment Guide](deployment.md) - Server deployment instructions
- [Configuration Guide](configuration.md) - Detailed configuration options
- [Troubleshooting Guide](troubleshooting.md) - Additional troubleshooting help
- [API Documentation](api.md) - API endpoints and integration details
