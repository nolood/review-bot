# GLM Code Review Bot CLI

A modern, production-ready CLI entry point for the GLM Code Review Bot with integrated monitoring capabilities.

## Features

- 🚀 **Modern CLI Interface**: Built with Typer and Rich for an excellent user experience
- 🔧 **Multiple Operation Modes**: Server mode, standalone bot, monitoring-only mode
- 🏥 **Health Checking**: Comprehensive health verification for all components
- ⚙️ **Configuration Validation**: Environment and configuration file validation
- 🌍 **Environment Support**: Development, staging, and production configurations
- 📊 **Monitoring Integration**: Full Prometheus metrics and health check integration
- 🛡️ **Production Ready**: Graceful shutdown, signal handling, error recovery
- 🐳 **Docker Optimized**: Designed for containerized deployments

## Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Make CLI executable
chmod +x review_bot_server.py
```

## Quick Start

```bash
# Show help
python3 review_bot_server.py --help

# Start development server with monitoring
python3 review_bot_server.py start-server --env dev

# Run bot standalone (dry run)
python3 review_bot_server.py run-bot --dry-run

# Check system health
python3 review_bot_server.py health-check

# Validate configuration
python3 review_bot_server.py validate-config
```

## Commands

### `start-server`

Start the review bot server with integrated monitoring and web interface.

```bash
python3 review_bot_server.py start-server [OPTIONS]

Options:
  --env, -e            Deployment environment [dev|staging|prod] (default: dev)
  --host                Server host address (default: 0.0.0.0)
  --port, -p           Server port (default: 8000)
  --monitoring-port     Monitoring server port (default: 8080)
  --log-level           Logging level (default: INFO)
  --workers             Number of worker processes (default: 1)
  --reload              Enable auto-reload for development
  --config              Configuration file path
  --no-monitoring       Disable monitoring server
  --no-cors             Disable CORS
  --verbose, -v         Enable verbose logging
```

**Examples:**

```bash
# Development with auto-reload
python3 review_bot_server.py start-server --env dev --reload --verbose

# Production deployment
python3 review_bot_server.py start-server --env prod --workers 4 --no-cors

# Custom ports and no monitoring
python3 review_bot_server.py start-server --port 9000 --no-monitoring
```

### `run-bot`

Run the review bot in standalone mode (single execution).

```bash
python3 review_bot_server.py run-bot [OPTIONS]

Options:
  --review-type, -t     Type of review [general|security|performance|code_style] (default: general)
  --project-id          GitLab project ID (overrides CI_PROJECT_ID)
  --mr-iid              Merge request IID (overrides CI_MERGE_REQUEST_IID)
  --dry-run             Run analysis without publishing comments
  --concurrent-limit     Max concurrent API requests (default: 3)
  --custom-prompt        Custom GLM analysis prompt
  --max-chunks          Maximum diff chunks to process
  --verbose, -v         Enable verbose logging
```

**Examples:**

```bash
# General review with verbose output
python3 review_bot_server.py run-bot --review-type general --verbose

# Security review on specific MR
python3 review_bot_server.py run-bot --review-type security --project-id 123 --mr-iid 456

# Dry run with custom prompt
python3 review_bot_server.py run-bot --dry-run --custom-prompt "Focus on performance issues"
```

### `health-check`

Run comprehensive health verification of all system components.

```bash
python3 review_bot_server.py health-check [OPTIONS]

Options:
  --verbose, -v         Enable verbose output
```

### `validate-config`

Validate configuration and environment variables.

```bash
python3 review_bot_server.py validate-config [OPTIONS]

Options:
  --config, -c          Configuration file to validate
  --verbose, -v         Enable verbose output
```

### `monitor-mode`

Run monitoring server only (no review bot functionality).

```bash
python3 review_bot_server.py monitor-mode [OPTIONS]

Options:
  --host                Monitoring server host (default: 0.0.0.0)
  --port, -p           Monitoring server port (default: 8080)
  --log-level           Logging level (default: INFO)
```

### `version`

Show version information.

```bash
python3 review_bot_server.py version
```

## Environment Configuration

### Required Environment Variables

```bash
# GitLab Configuration
export GITLAB_TOKEN="your-gitlab-token"
export GITLAB_API_URL="https://gitlab.example.com/api/v4"

# GLM Configuration  
export GLM_API_KEY="your-glm-api-key"
export GLM_API_URL="https://api.z.ai/api/paas/v4/chat/completions"

# GitLab CI Context (auto-provided in CI/CD)
export CI_PROJECT_ID="123"
export CI_MERGE_REQUEST_IID="456"
```

### Optional Environment Variables

```bash
# Server Configuration
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="8000"
export MONITORING_PORT="8080"

# Performance Configuration
export MAX_CONCURRENT_REVIEWS="3"
export REVIEW_TIMEOUT_SECONDS="300"

# Logging Configuration
export LOG_LEVEL="INFO"
export LOG_FORMAT="json"  # text | json

# Retry Configuration
export MAX_RETRIES="3"
export RETRY_DELAY="1.0"
export RETRY_BACKOFF_FACTOR="2.0"
```

## Environment-Specific Behavior

### Development (`--env dev`)
- Auto-reload enabled by default
- Verbose logging
- CORS enabled for all origins
- Single worker process
- Extended timeouts

### Staging (`--env staging`) 
- Production-like configuration
- Comprehensive logging
- CORS for specific domains
- Multiple workers optional
- Standard timeouts

### Production (`--env prod`)
- Optimized for performance
- JSON structured logging
- CORS disabled by default
- Multiple workers recommended
- Strict timeouts
- Enhanced security settings

## Configuration Files

The CLI supports JSON configuration files for complex deployments:

```json
{
  "server_host": "0.0.0.0",
  "server_port": 8000,
  "enable_cors": true,
  "cors_origins": ["https://app.example.com"],
  "max_concurrent_reviews": 5,
  "review_timeout_seconds": 300,
  "log_level": "INFO",
  "log_format": "json",
  "monitoring_enabled": true,
  "monitoring_port": 8080,
  "max_retries": 3,
  "retry_delay": 1.0,
  "api_request_delay": 0.5
}
```

```bash
# Use configuration file
python3 review_bot_server.py start-server --config production.json
```

## Monitoring Integration

When running in server mode, the CLI automatically starts:

1. **Main Application Server** (port 8000 by default)
   - REST API for review management
   - Web interface for manual operations
   - Background task processing

2. **Monitoring Server** (port 8080 by default)
   - Health check endpoints (`/health`, `/health/detailed`)
   - Prometheus metrics (`/metrics`, `/metrics/prometheus`)
   - Administrative endpoints (`/admin/config`, `/admin/reset-metrics`)
   - Server information (`/`)

### Health Check Endpoints

```bash
# Basic health check
curl http://localhost:8080/health

# Detailed health with all subsystems
curl http://localhost:8080/health/detailed

# Specific health check
curl http://localhost:8080/health/checker/gitlab
```

### Metrics Endpoints

```bash
# All metrics in JSON format
curl http://localhost:8080/metrics

# Prometheus format
curl http://localhost:8080/metrics/prometheus

# Available registries
curl http://localhost:8080/metrics/registries
```

## Docker Deployment

### Basic Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN chmod +x review_bot_server.py

EXPOSE 8000 8080

CMD ["python3", "review_bot_server.py", "start-server", "--env", "prod"]
```

### Docker Compose

```yaml
version: '3.8'
services:
  review-bot:
    build: .
    ports:
      - "8000:8000"   # Main server
      - "8080:8080"   # Monitoring
    environment:
      - GITLAB_TOKEN=${GITLAB_TOKEN}
      - GLM_API_KEY=${GLM_API_KEY}
      - LOG_LEVEL=INFO
      - MAX_CONCURRENT_REVIEWS=3
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

## Signal Handling and Graceful Shutdown

The CLI implements comprehensive signal handling:

- **SIGTERM**: Graceful shutdown (Docker stop, systemd)
- **SIGINT**: User interruption (Ctrl+C)
- **SIGUSR1**: Log current status (for debugging)

During graceful shutdown:
1. Accept no new requests
2. Cancel in-progress background tasks
3. Close all client connections
4. Cleanup resources
5. Shutdown servers cleanly

## Error Handling

The CLI provides comprehensive error handling:

1. **Configuration Errors**: Clear validation messages
2. **Dependency Issues**: Graceful fallbacks and warnings
3. **Runtime Errors**: Detailed error logs with context
4. **Network Issues**: Automatic retries with backoff
5. **Resource Limits**: Protection against memory/CPU exhaustion

## Performance Considerations

- **Async/Await**: Non-blocking I/O throughout
- **Connection Pooling**: Reused HTTP connections
- **Request Batching**: Concurrent API requests
- **Memory Management**: Configurable limits and cleanup
- **CPU Optimization**: Efficient diff processing
- **Rate Limiting**: Respect API limits and backpressure

## Security Features

- **Token Redaction**: Sensitive data in logs is masked
- **CORS Control**: Configurable cross-origin policies
- **Input Validation**: Comprehensive parameter validation
- **Error Sanitization**: No sensitive data in error responses
- **Request Signing**: Optional API request signing

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed
2. **Permission Denied**: Make the script executable: `chmod +x review_bot_server.py`
3. **Port Conflicts**: Use different ports or check for existing processes
4. **Environment Variables**: Verify all required variables are set
5. **Network Issues**: Check firewall and proxy settings

### Debug Mode

```bash
# Enable verbose debugging
python3 review_bot_server.py --verbose --log-level DEBUG

# Check configuration
python3 review_bot_server.py validate-config --verbose

# Health check with details
python3 review_bot_server.py health-check --verbose
```

## Development

### Adding New Commands

1. Add the command function to the CLI file
2. Use Typer decorators for arguments and options
3. Implement async/await for I/O operations
4. Add comprehensive error handling
5. Include rich output formatting
6. Update this documentation

### Testing

```bash
# Test CLI structure
python3 test_cli_demo.py

# Test with mock environment
python3 -m pytest tests/test_cli.py -v
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.