.PHONY: help install test lint format clean run

# Default target
help:
	@echo "Available commands:"
	@echo "  install    - Install dependencies"
	@echo "  test       - Run tests"
	@echo "  lint       - Run linting"
	@echo "  format     - Format code"
	@echo "  clean      - Clean up generated files"
	@echo "  run        - Run the review bot (requires env vars)"

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Run tests
test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Run linting
lint:
	flake8 src/ tests/ --max-line-length=120
	mypy src/ --ignore-missing-imports

# Format code
format:
	black src/ tests/
	isort src/ tests/

# Clean up
clean:
	find . -type d -name __pycache__ -delete
	find . -type f -name "*.pyc" -delete
	rm -rf build/ dist/ *.egg-info/
	rm -rf htmlcov/ .coverage
	rm -rf review_logs/

# Run the review bot
run:
	python review_bot.py

# Docker build
docker-build:
	docker build -t gitlab-code-review-bot .

# Docker run
docker-run:
	docker run --rm -it \
		-e GLM_API_KEY=$(GLM_API_KEY) \
		-e GITLAB_TOKEN=$(GITLAB_TOKEN) \
		-e CI_PROJECT_ID=$(CI_PROJECT_ID) \
		-e CI_MERGE_REQUEST_IID=$(CI_MERGE_REQUEST_IID) \
		gitlab-code-review-bot