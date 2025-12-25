# Webhook Integration Quick Start

Quick reference for setting up GitLab webhook integration with the review bot.

## 1. Generate Secret Token

```bash
# Generate a secure 32-character secret
WEBHOOK_SECRET=$(openssl rand -hex 32)
echo "Webhook Secret: $WEBHOOK_SECRET"
```

## 2. Deploy Bot Server

```bash
# Using Docker Compose (recommended)
docker compose up -d

# Or using Docker directly
docker run -d \
  --name review-bot \
  -p 8000:8000 \
  -p 8080:8080 \
  -e GITLAB_TOKEN="your_token" \
  -e GLM_API_KEY="your_key" \
  -e WEBHOOK_SECRET="$WEBHOOK_SECRET" \
  -e WEBHOOK_ENABLED="true" \
  review-bot:latest
```

## 3. Configure in GitLab

1. Go to **Project Settings** > **Integrations** > **Webhooks**
2. Click **Add webhook**
3. Fill in:
   - **URL:** `https://your-bot-domain/webhook/gitlab`
   - **Secret token:** Paste the `WEBHOOK_SECRET` value
   - **Trigger:** Check "Merge request events"
   - **SSL verification:** Enabled
4. Click **Add webhook**

## 4. Test the Webhook

In GitLab webhook settings:
1. Click your webhook entry
2. Scroll to "Recent deliveries"
3. Click the test button
4. Check status (should be 200 or 202)

## 5. Verify in Logs

```bash
# View bot logs
docker logs -f review-bot

# Look for: "Webhook passed all validation and filters"
```

## Essential Environment Variables

```bash
# Required
GITLAB_TOKEN=your_gitlab_token
GLM_API_KEY=your_glm_api_key
WEBHOOK_SECRET=your_generated_secret

# Webhook Settings
WEBHOOK_ENABLED=true
WEBHOOK_VALIDATE_SIGNATURE=true
WEBHOOK_SKIP_DRAFT=true
WEBHOOK_SKIP_WIP=true

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=8000

# Deduplication (recommended)
DEDUPLICATION_STRATEGY=DELETE_SUMMARY_ONLY
```

## Deduplication Strategies

| Strategy | Behavior | Use Case |
|----------|----------|----------|
| `DELETE_SUMMARY_ONLY` | Keep inline comments, replace summary | **Recommended** - balanced approach |
| `DELETE_ALL` | Remove all previous comments | Clean slate, high-frequency updates |
| `KEEP_ALL` | Keep everything | Compliance/audit trails |
| `DELETE_OUTDATED` | Remove old commit comments | Commit-level tracking |

## Common Issues

### Webhook Not Triggered
- Check URL is publicly accessible
- Verify "Merge request events" is enabled
- Check GitLab recent deliveries for errors

### Invalid Signature Error
- Verify `WEBHOOK_SECRET` matches GitLab setting
- Ensure no extra spaces in secret
- Regenerate secret if needed

### Comments Not Appearing
- Check `GITLAB_TOKEN` has `api` and `write_repository` scopes
- Verify `GLM_API_KEY` is valid
- Check bot logs: `docker logs review-bot | grep -i error`

## Monitoring

```bash
# Health check
curl https://your-bot-domain/health

# View metrics
curl https://your-bot-domain/api/v1/status

# View recent deliveries in GitLab
# Settings > Integrations > Webhooks > [Your webhook]
```

## File References

Key implementation files:
- `/home/nolood/general/review-bot/src/app_server.py` - Flask/FastAPI server
- `/home/nolood/general/review-bot/src/webhook/handlers.py` - Webhook handler
- `/home/nolood/general/review-bot/src/webhook/validators.py` - Signature validation
- `/home/nolood/general/review-bot/src/deduplication/comment_tracker.py` - Deduplication

## Full Documentation

See [Webhook Setup Guide](docs/webhook_setup.md) for complete instructions including:
- Detailed GitLab configuration steps
- All environment variables with descriptions
- Complete Docker Compose configuration
- NGINX reverse proxy setup with TLS
- Troubleshooting 8 common issues
- Security best practices
- Manual webhook testing

## Support

For detailed help:
1. Check [Troubleshooting Guide](docs/webhook_setup.md#troubleshooting)
2. Review server logs: `docker logs review-bot`
3. Check GitLab webhook deliveries in Settings > Integrations > Webhooks
4. Refer to [Deployment Guide](docs/deployment.md) for server setup
