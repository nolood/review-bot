#!/usr/bin/env python3
"""
Simple integration test for monitoring components.
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))


async def test_individual_components():
    """Test each monitoring component individually."""
    print("Testing Monitoring Components Individually\n")
    print("=" * 50)
    
    # Test Health Checker
    print("1. Testing Health Checker...")
    try:
        from monitoring.health_checker import HealthChecker
        health_checker = HealthChecker()
        print(f"   ✓ HealthChecker created")
        print(f"   ✓ Available checkers: {health_checker.get_checker_names()}")
        
        # Test status summary
        summary = await health_checker.get_status_summary()
        print(f"   ✓ Status summary: {summary}")
        
    except Exception as e:
        print(f"   ✗ HealthChecker failed: {e}")
    
    print()
    
    # Test Metrics Collector
    print("2. Testing Metrics Collector...")
    try:
        from monitoring.metrics_collector import MetricsCollector
        metrics_collector = MetricsCollector()
        print(f"   ✓ MetricsCollector created")
        
        # Record test API request
        metrics_collector.record_api_request(
            api_name="test_api",
            method="GET", 
            status_code=200,
            response_time_ms=150.5
        )
        print(f"   ✓ API request recorded")
        
        # Get metrics
        metrics = metrics_collector.get_all_metrics()
        print(f"   ✓ Metrics retrieved: {len(metrics)} keys")
        
        # Get Prometheus metrics
        prometheus = metrics_collector.get_prometheus_metrics()
        print(f"   ✓ Prometheus metrics: {len(prometheus)} characters")
        
    except Exception as e:
        print(f"   ✗ MetricsCollector failed: {e}")
    
    print()
    
    # Test Alert Manager
    print("3. Testing Alert Manager...")
    try:
        from monitoring.alerts import AlertManager, AlertRule, AlertSeverity
        alert_manager = AlertManager()
        print(f"   ✓ AlertManager created")
        
        # List default rules
        rules = alert_manager.list_rules()
        print(f"   ✓ Default rules: {len(rules)}")
        
        # Add custom rule
        custom_rule = AlertRule(
            name="test_rule",
            description="Test rule for integration testing",
            severity=AlertSeverity.INFO,
            metric_name="test_metric",
            threshold_value=50.0
        )
        alert_manager.add_rule(custom_rule)
        print(f"   ✓ Custom rule added")
        
        # Evaluate rules with test metrics
        test_metrics = {"test_metric": 75.0}
        alerts = alert_manager.evaluate_rules(metrics=test_metrics)
        print(f"   ✓ Rules evaluated: {len(alerts)} alerts triggered")
        
    except Exception as e:
        print(f"   ✗ AlertManager failed: {e}")
    
    print()
    
    # Test Monitoring Server
    print("4. Testing Monitoring Server...")
    try:
        from monitoring.monitoring_server import MonitoringServer, ServerConfig
        from monitoring.health_checker import HealthChecker
        from monitoring.metrics_collector import MetricsCollector
        
        health_checker = HealthChecker()
        metrics_collector = MetricsCollector()
        
        config = ServerConfig(host="127.0.0.1", port=8080)
        server = MonitoringServer(
            health_checker=health_checker,
            metrics_collector=metrics_collector,
            config=config
        )
        print(f"   ✓ MonitoringServer created")
        print(f"   ✓ Server config: {config.host}:{config.port}")
        
        # Get FastAPI app
        app = server.get_app()
        print(f"   ✓ FastAPI app: {app.title}")
        
    except Exception as e:
        print(f"   ✗ MonitoringServer failed: {e}")
    
    print("=" * 50)
    print("All component tests completed!")


async def main():
    """Run integration tests."""
    try:
        await test_individual_components()
        return 0
    except Exception as e:
        print(f"Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)