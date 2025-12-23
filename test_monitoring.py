#!/usr/bin/env python3
"""
Test script for the monitoring module.

This script demonstrates the functionality of the monitoring components
and can be used for development and testing purposes.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.monitoring import (
    HealthChecker, 
    MetricsCollector, 
    MonitoringServer, 
    AlertManager,
    AlertRule,
    AlertSeverity,
    AlertStatus
)


async def test_health_checker():
    """Test health checker functionality."""
    print("Testing Health Checker...")
    
    health_checker = HealthChecker()
    
    # Test status summary
    summary = await health_checker.get_status_summary()
    print(f"Health checker summary: {summary}")
    
    # Test full health check
    results = await health_checker.check_all()
    print(f"Health check results: {results}")
    
    print("Health checker test completed.\n")


async def test_metrics_collector():
    """Test metrics collector functionality."""
    print("Testing Metrics Collector...")
    
    metrics_collector = MetricsCollector()
    metrics_collector.start_collection()
    
    # Record some test API requests
    metrics_collector.record_api_request(
        api_name="test_api",
        method="GET",
        status_code=200,
        response_time_ms=150.5
    )
    
    metrics_collector.record_api_request(
        api_name="test_api", 
        method="POST",
        status_code=500,
        response_time_ms=2000.0,
        error=Exception("Test error")
    )
    
    # Record token usage
    metrics_collector.record_token_usage(
        prompt_tokens=100,
        completion_tokens=50,
        model="test-model"
    )
    
    # Get metrics
    all_metrics = metrics_collector.get_all_metrics()
    print(f"Collected metrics: {all_metrics}")
    
    # Get Prometheus metrics
    prometheus_metrics = metrics_collector.get_prometheus_metrics()
    print(f"Prometheus metrics preview: {prometheus_metrics[:200]}...")
    
    metrics_collector.stop_collection()
    print("Metrics collector test completed.\n")


async def test_alert_manager():
    """Test alert manager functionality."""
    print("Testing Alert Manager...")
    
    alert_manager = AlertManager()
    
    # List default rules
    rules = alert_manager.list_rules()
    print(f"Default alert rules: {[r.name for r in rules]}")
    
    # Create test metrics
    test_metrics = {
        "cpu_percent": 85.0,
        "memory_percent": 90.0,
        "disk_percent": 95.0,
        "error_rate": 0.15
    }
    
    # Evaluate rules (should trigger some alerts)
    triggered_alerts = alert_manager.evaluate_rules(metrics=test_metrics)
    print(f"Triggered alerts: {len(triggered_alerts)}")
    
    for alert in triggered_alerts:
        print(f"  - {alert.severity.value.upper()}: {alert.message}")
    
    # Get alert statistics
    stats = alert_manager.get_alert_statistics()
    print(f"Alert statistics: {stats}")
    
    print("Alert manager test completed.\n")


def test_monitoring_server():
    """Test monitoring server functionality."""
    print("Testing Monitoring Server...")
    
    # Create components
    health_checker = HealthChecker()
    metrics_collector = MetricsCollector()
    
    # Create server
    server = MonitoringServer(
        health_checker=health_checker,
        metrics_collector=metrics_collector
    )
    
    print(f"Server configuration: {server.config}")
    print(f"Available endpoints: {len(server.app.routes)}")
    
    # Get FastAPI app
    app = server.get_app()
    print(f"FastAPI app created: {app.title}")
    
    print("Monitoring server test completed.\n")


async def main():
    """Run all tests."""
    print("Starting Monitoring Module Tests\n")
    print("=" * 50)
    
    try:
        # Test individual components
        await test_health_checker()
        await test_metrics_collector()
        await test_alert_manager()
        test_monitoring_server()
        
        print("=" * 50)
        print("All tests completed successfully!")
        
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)