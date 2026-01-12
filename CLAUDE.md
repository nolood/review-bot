# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

GLM Code Review Bot - An automated code review bot for GitLab that uses the GLM-4 model to analyze merge requests and post structured comments. Built with Python 3.11+, FastAPI, and async/await architecture.

## Common Commands

```bash
# Install dependencies
make install
# Or manually:
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
make test
# Or: pytest tests/ -v --cov=src

# Run a single test file
pytest tests/test_glm_client.py -v

# Run tests matching a pattern
pytest -k "test_comment" -v

# Lint and type check
make lint
# Or: flake8 src/ tests/ --max-line-length=120 && mypy src/ --ignore-missing-imports

# Format code
make format
# Or: black src/ tests/ && isort src/ tests/

# Run the server (do not start dev app per user preferences)
# python review_bot_server.py server

# Docker
docker-compose up -d          # Development
docker-compose -f docker-compose.prod.yml up -d  # Production
```

## Architecture

### Entry Points
- `review_bot_server.py` - Main CLI entry point with Typer, supports server mode, standalone bot execution, and health checks
- `src/app_server.py` - FastAPI server for webhook handling and web interface

### Core Components (src/)
- `gitlab_client_async.py` - Async GitLab API client for fetching MR diffs and posting comments
- `glm_client_async.py` - Async GLM-4 API client with retry logic and token tracking
- `diff_parser.py` - Parses GitLab diffs, handles chunking for large files, extracts line numbers
- `comment_publisher.py` - Formats and publishes review comments (inline and general)
- `review_processor_async.py` - Orchestrates the async review workflow
- `line_code_mapper.py` - Maps line numbers to GitLab line codes for inline comments
- `client_manager_async.py` - Manages async client lifecycle

### Configuration (src/config/)
- `settings.py` - Pydantic-based settings with environment variable management
- `prompts.py` - GLM prompts and ReviewType enum definitions

### Webhook System (src/webhook/)
- `handlers.py` - GitLab webhook event handlers
- `validators.py` - Webhook payload validation
- `models.py` - Webhook data models

### Deduplication (src/deduplication/)
- `commit_tracker.py` - Tracks processed commits to avoid duplicate reviews
- `comment_tracker.py` - Tracks posted comments to avoid duplicates

### Utilities (src/utils/)
- `logger.py` - Structured logging with sensitive data filtering

## Key Environment Variables

Required:
- `GLM_API_KEY` - GLM API key
- `GITLAB_TOKEN` - GitLab Personal Access Token with `api` scope
- `GITLAB_API_URL` - GitLab API URL

Optional:
- `GLM_TEMPERATURE` - Model temperature (default: 0.3)
- `MAX_DIFF_SIZE` - Maximum diff size in tokens (default: 50000)
- `LOG_LEVEL` - Logging level (default: INFO)

## Testing

Tests are in `tests/` with pytest markers:
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests

Uses pytest-asyncio for async test support. Mock external APIs with respx for httpx.

## Code Style

- Line length: 120 characters
- Formatter: black
- Import sorting: isort
- Type checking: mypy
- Async/await throughout for I/O operations
- Pydantic for data validation and settings
