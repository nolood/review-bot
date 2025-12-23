# GLM Code Review Bot - Application Server

A production-ready FastAPI server that integrates the GLM Code Review Bot with monitoring and web interface capabilities.

## Features

### 🚀 Core Server Features
- **FastAPI Web Server**: High-performance async web framework
- **RESTful API**: Complete API for review management
- **Background Task Processing**: Async review processing with concurrent support
- **Web Interface**: User-friendly web UI for triggering and monitoring reviews
- **Production Ready**: Full middleware, error handling, and security

### 📊 Monitoring Integration
- **Health Checks**: Comprehensive health monitoring endpoints
- **Metrics Collection**: Built-in metrics for monitoring and alerting
- **Administrative Endpoints**: Admin interface for server management
- **Graceful Shutdown**: Proper cleanup and resource management

### 🛡️ Security & Reliability
- **CORS Support**: Configurable Cross-Origin Resource Sharing
- **GZIP Compression**: Response compression for better performance
- **Request Logging**: Comprehensive request/response logging
- **Error Handling**: Structured error handling and reporting
- **Signal Handling**: Graceful shutdown on SIGTERM/SIGINT

## Quick Start

### Installation
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn pydantic
```

### Running the Server

#### Development Mode
```bash
# Run with auto-reload
python -m src.app_server --reload --host 0.0.0.0 --port 8000
```

#### Production Mode
```bash
# Run with multiple workers
python -m src.app_server --workers 4 --host 0.0.0.0 --port 8000
```

#### Custom Configuration
```bash
# Custom host and port
python -m src.app_server --host 127.0.0.1 --port 8080

# With monitoring
python -m src.app_server --monitoring-port 8081

# Without monitoring
python -m src.app_server --no-monitoring
```

## API Documentation

### Review Management

#### Trigger a Review
```bash
curl -X POST "http://localhost:8000/api/v1/reviews" \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": "123",
    "mr_iid": "456",
    "force_review": false
  }'
```

#### Get Review Status
```bash
curl "http://localhost:8000/api/v1/reviews/{task_id}/status"
```

#### List Reviews
```bash
curl "http://localhost:8000/api/v1/reviews?limit=10&status=completed"
```

#### Cancel a Review
```bash
curl -X DELETE "http://localhost:8000/api/v1/reviews/{task_id}"
```

### Server Status

#### Health Check
```bash
curl "http://localhost:8000/health"
```

#### Server Status
```bash
curl "http://localhost:8000/api/v1/status"
```

#### Configuration
```bash
curl "http://localhost:8000/api/v1/admin/config"
```

#### Graceful Shutdown
```bash
curl -X POST "http://localhost:8000/api/v1/admin/shutdown"
```

## Web Interface

Access the web interface at `http://localhost:8000` for:

- 📊 Visual review status dashboard
- 🚀 Easy review triggering form
- 📋 Review history and progress
- ⚙️ Server configuration view

## Configuration

### Environment Variables
```bash
# GitLab Configuration
export GITLAB_TOKEN="your-gitlab-token"
export GITLAB_API_URL="https://gitlab.com/api/v4"
export CI_PROJECT_ID="123"
export CI_MERGE_REQUEST_IID="456"

# GLM Configuration
export GLM_API_KEY="your-glm-api-key"
export GLM_API_URL="https://api.z.ai/api/paas/v4/chat/completions"

# Server Configuration
export SERVER_HOST="0.0.0.0"
export SERVER_PORT="8000"
export LOG_LEVEL="INFO"

# Monitoring Configuration
export MONITORING_ENABLED="true"
export MONITORING_PORT="8080"

# Performance Configuration
export MAX_CONCURRENT_REVIEWS="3"
export REVIEW_TIMEOUT_SECONDS="300"
```

### Server Config Options
```python
from src.app_server import ServerConfig

config = ServerConfig(
    host="0.0.0.0",              # Server bind address
    port=8000,                       # Server port
    log_level="info",                 # Logging level
    enable_cors=True,                 # Enable CORS
    cors_origins=["*"],                # CORS allowed origins
    enable_compression=True,           # Enable GZIP compression
    max_concurrent_reviews=3,          # Max concurrent reviews
    review_timeout_seconds=300,         # Review timeout
    enable_monitoring=True,            # Enable monitoring server
    monitoring_port=8080,             # Monitoring server port
    workers=1,                         # Number of worker processes
    reload=False                       # Enable auto-reload
)
```

## Architecture

### Components

#### AppServer
Main application server class that orchestrates all components:
- FastAPI application setup
- Middleware configuration
- Route registration
- Lifecycle management

#### Background Processing
- **Async Task Queue**: Manages review tasks with concurrent processing
- **Task History**: Maintains review history with configurable size limits
- **Progress Tracking**: Real-time progress updates for long-running reviews

#### Monitoring Integration
- **Health Checks**: Periodic health monitoring of external dependencies
- **Metrics Collection**: Performance metrics and usage statistics
- **Admin Interface**: Administrative endpoints for server management

### Request Flow

1. **Review Request** → API endpoint validates request
2. **Task Creation** → Background task created and queued
3. **Concurrent Processing** → Task processed with timeout handling
4. **Progress Updates** → Real-time status updates
5. **Completion** → Results stored and notifications sent

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/

EXPOSE 8000

CMD ["python", "-m", "src.app_server", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  review-bot:
    build: .
    ports:
      - "8000:8000"
      - "8080:8080"
    environment:
      - GITLAB_TOKEN=${GITLAB_TOKEN}
      - GLM_API_KEY=${GLM_API_KEY}
      - SERVER_HOST=0.0.0.0
      - SERVER_PORT=8000
      - MONITORING_ENABLED=true
      - MONITORING_PORT=8080
    restart: unless-stopped
```

### Systemd Service
```ini
[Unit]
Description=GLM Code Review Bot
After=network.target

[Service]
Type=simple
User=reviewbot
WorkingDirectory=/opt/review-bot
Environment=PATH=/opt/review-bot/venv/bin
ExecStart=/opt/review-bot/venv/bin/python -m src.app_server
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

## Monitoring

### Health Endpoints
- `/health` - Basic health check
- `/health/detailed` - Comprehensive health status
- `/api/v1/status` - Server statistics and status

### Metrics
- **Review Metrics**: Reviews processed, success/failure rates, processing times
- **System Metrics**: Memory usage, CPU load, active connections
- **API Metrics**: Request counts, response times, error rates

### Logs
Structured logging with context:
```json
{
  "timestamp": "2025-12-22T16:30:16Z",
  "level": "INFO",
  "logger": "app_server",
  "message": "Review completed successfully",
  "extra": {
    "task_id": "uuid-here",
    "project_id": "123",
    "mr_iid": "456",
    "duration_seconds": 15.2
  }
}
```

## Security

### Authentication
- GitLab token authentication for API access
- Configurable CORS policies
- Request rate limiting
- Input validation and sanitization

### Best Practices
- Secrets management via environment variables
- Secure default configurations
- Request/response logging without sensitive data
- Graceful degradation when dependencies unavailable

## Development

### Running Tests
```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
python test_app_server.py
```

### Code Structure
```
src/
├── app_server.py              # Main application server
├── config/                    # Configuration management
├── monitoring/                # Monitoring components
├── utils/                     # Utilities and helpers
├── client_manager_async.py     # Async client management
├── review_processor_async.py   # Async review processing
└── chunk_processor_async.py    # Async chunk processing
```

## Troubleshooting

### Common Issues

#### Server Won't Start
```bash
# Check dependencies
python -c "import fastapi, uvicorn, pydantic"

# Check configuration
python -m src.app_server --help
```

#### Reviews Not Processing
- Check GitLab API token and permissions
- Verify GLM API key and connectivity
- Review server logs for error details
- Check concurrent review limits

#### Monitoring Issues
- Verify monitoring port availability
- Check firewall rules
- Review monitoring server logs

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with single worker and reload
python -m src.app_server --workers 1 --reload --log-level debug
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Create an issue in the project repository
- Check the documentation for troubleshooting steps
- Review server logs for detailed error information