#!/usr/bin/env python3
"""
Monitoring Demo for Review Bot
Demonstrates the complete monitoring stack capabilities
"""

import asyncio
import time
import logging
from typing import Dict, Any

from prometheus_client import Counter, Histogram, Gauge, start_http_server, Info
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
import uvicorn
import psutil

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter('review_bot_requests_total', 'Total review requests', ['method', 'endpoint'])
REQUEST_DURATION = Histogram('review_bot_request_duration_seconds', 'Request duration in seconds')
ACTIVE_REVIEWS = Gauge('review_bot_active_reviews', 'Number of active reviews')
ERROR_COUNT = Counter('review_bot_errors_total', 'Total errors', ['error_type'])
SYSTEM_INFO = Info('review_bot_system_info', 'System information')

# FastAPI app
app = FastAPI(title="Review Bot Monitoring", version="1.0.0")

class MonitoringDemo:
    """Demo class to simulate review bot operations with monitoring"""
    
    def __init__(self):
        self.active_reviews = 0
        self.total_requests = 0
        
    @REQUEST_DURATION.time()
    async def simulate_review_request(self, difficulty: str = "medium") -> Dict[str, Any]:
        """Simulate a review request with monitoring"""
        REQUEST_COUNT.labels(method="POST", endpoint="/review").inc()
        ACTIVE_REVIEWS.set(self.active_reviews)
        
        # Simulate review processing time based on difficulty
        if difficulty == "easy":
            processing_time = 2
            success_rate = 0.95
        elif difficulty == "medium":
            processing_time = 5
            success_rate = 0.85
        else:  # hard
            processing_time = 10
            success_rate = 0.75
            
        logger.info(f"Processing {difficulty} review (will take {processing_time}s)")
        
        # Simulate processing
        self.active_reviews += 1
        ACTIVE_REVIEWS.set(self.active_reviews)
        
        try:
            await asyncio.sleep(processing_time)
            
            # Simulate occasional errors
            import random
            if random.random() > success_rate:
                error_type = "parsing_error" if random.random() > 0.5 else "api_error"
                ERROR_COUNT.labels(error_type=error_type).inc()
                raise Exception(f"Simulated {error_type}")
            
            self.total_requests += 1
            result = {
                "review_id": f"review_{self.total_requests}",
                "difficulty": difficulty,
                "processing_time": processing_time,
                "status": "completed"
            }
            
            logger.info(f"Review completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Review failed: {e}")
            raise
        finally:
            self.active_reviews -= 1
            ACTIVE_REVIEWS.set(self.active_reviews)

# Initialize demo
demo = MonitoringDemo()

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return JSONResponse({
        "status": "healthy",
        "timestamp": time.time(),
        "active_reviews": demo.active_reviews,
        "total_requests": demo.total_requests
    })

@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint - served by prometheus_client"""
    pass  # Handled by prometheus_client

@app.get("/simulate-review")
async def simulate_review(difficulty: str = "medium"):
    """Simulate a review request for testing"""
    try:
        result = await demo.simulate_review_request(difficulty)
        return JSONResponse(result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/system-info")
async def system_info():
    """Get system information"""
    cpu_percent = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    info = {
        "cpu_percent": cpu_percent,
        "memory_percent": memory.percent,
        "disk_percent": disk.percent,
        "active_reviews": demo.active_reviews,
        "total_requests": demo.total_requests
    }
    
    # Update system info metric
    SYSTEM_INFO.info(info)
    
    return JSONResponse(info)

async def run_simulation():
    """Run continuous simulation of review requests"""
    difficulties = ["easy", "medium", "hard"]
    
    while True:
        try:
            difficulty = difficulties[int(time.time()) % 3]
            await demo.simulate_review_request(difficulty)
            await asyncio.sleep(3)  # Wait between requests
        except Exception as e:
            logger.error(f"Simulation error: {e}")
            await asyncio.sleep(1)

async def main():
    """Main function to start monitoring and simulation"""
    logger.info("Starting Review Bot Monitoring Demo")
    
    # Update system info
    SYSTEM_INFO.info({
        "version": "1.0.0",
        "environment": "demo",
        "service": "review-bot"
    })
    
    # Start metrics server
    start_http_server(8000)
    logger.info("Metrics server started on port 8000")
    
    # Start simulation in background
    asyncio.create_task(run_simulation())
    
    # Start FastAPI server
    config = uvicorn.Config(app, host="0.0.0.0", port=8001, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info("Health check server started on port 8001")
    logger.info("Visit http://localhost:8000/metrics for Prometheus metrics")
    logger.info("Visit http://localhost:8001/health for health check")
    logger.info("Visit http://localhost:8001/simulate-review for manual review simulation")
    logger.info("Visit http://localhost:8001/system-info for system information")
    
    await server.serve()

if __name__ == "__main__":
    asyncio.run(main())