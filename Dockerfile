FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies including monitoring tools
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    wget \
    git \
    netcat-openbsd \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Install additional monitoring dependencies
RUN pip install --no-cache-dir \
    prometheus-client==0.19.0 \
    psutil==5.9.6 \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs review_logs config monitoring

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose ports for metrics and health checks
EXPOSE 8000 8001

# Enhanced health check with monitoring endpoints
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (will be overridden in CI)
CMD ["python", "review_bot_server.py", "start-server", "--env", "prod"]