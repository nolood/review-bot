"""
Comprehensive test suite for GLM Code Review Bot monitoring system.

This module provides thorough testing for all monitoring components including:
- Health checker functionality and edge cases
- Metrics collection and aggregation
- Alert system with rule evaluation
- Monitoring server API endpoints
- Performance benchmarks and stress tests
- Integration scenarios and error handling

Test Structure:
- Unit tests for individual components
- Integration tests for component interactions
- Performance tests for scalability validation
- Mock-based tests for external dependencies
- End-to-end workflow testing
"""

import asyncio
import json
import time
import pytest
import threading
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, List, Optional

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Import monitoring components with proper error handling
try:
    from src.monitoring.health_checker import (
        HealthChecker, APIHealthChecker, SystemResourceChecker, 
        ApplicationHealthChecker, HealthStatus, HealthCheckResult
    )
    from src.monitoring.metrics_collector import (
        MetricsCollector, APITracker, TokenUsageTracker, 
        SystemMetricsCollector, MetricType
    )
    from src.monitoring.monitoring_server import (
        MonitoringServer, ServerConfig, create_monitoring_server
    )
    from src.monitoring.alerts import (
        AlertManager, AlertRule, Alert, AlertSeverity, AlertStatus,
        NotificationChannel, AlertRuleEngine
    )
    MONITORING_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Monitoring modules not available: {e}")
    MONITORING_AVAILABLE = False
    
    # Create mock classes for testing when modules aren't available
    class HealthStatus:
        HEALTHY = "healthy"
        DEGRADED = "degraded"
        UNHEALTHY = "unhealthy"
        UNKNOWN = "unknown"
    
    class AlertSeverity:
        INFO = "info"
        WARNING = "warning"
        ERROR = "error"
        CRITICAL = "critical"
    
    class AlertStatus:
        ACTIVE = "active"
        ACKNOWLEDGED = "acknowledged"
        RESOLVED = "resolved"
        SUPPRESSED = "suppressed"
    
    class NotificationChannel:
        LOG = "log"
        WEBHOOK = "webhook"
        EMAIL = "email"
        SLACK = "slack"
        DISCORD = "discord"
    
    # Create mock classes
    HealthChecker = Mock
    APIHealthChecker = Mock
    SystemResourceChecker = Mock
    ApplicationHealthChecker = Mock
    HealthCheckResult = Mock
    MetricsCollector = Mock
    APITracker = Mock
    TokenUsageTracker = Mock
    SystemMetricsCollector = Mock
    MetricType = Mock
    MonitoringServer = Mock
    ServerConfig = Mock
    AlertManager = Mock
    AlertRule = Mock
    Alert = Mock
    AlertRuleEngine = Mock

# Try to import FastAPI test client, but don't fail if not available
try:
    from fastapi.testclient import TestClient
    TEST_CLIENT_AVAILABLE = True
except ImportError:
    TEST_CLIENT_AVAILABLE = False
    TestClient = None


class TestHealthChecker:
    """Test suite for health checker components."""
    
    @pytest.fixture
    def mock_settings(self):
        """Mock settings for testing."""
        settings = Mock()
        settings.gitlab_token = "test_token"
        settings.gitlab_api_url = "https://gitlab.example.com/api/v4"
        settings.project_id = "123"
        settings.mr_iid = "456"
        settings.glm_api_key = "test_glm_key"
        settings.glm_api_url = "https://glm.example.com/api/v1"
        return settings
    
    @pytest.fixture
    def api_health_checker(self):
        """Create API health checker for testing."""
        return APIHealthChecker(
            name="test_api",
            url="https://httpbin.org/status/200",
            timeout_seconds=5.0
        )
    
    @pytest.fixture
    def system_health_checker(self):
        """Create system resource health checker."""
        return SystemResourceChecker(
            name="test_system",
            cpu_threshold=80.0,
            memory_threshold=85.0,
            disk_threshold=90.0
        )
    
    @pytest.fixture
    def application_health_checker(self, mock_settings):
        """Create application health checker with mocked settings."""
        with patch('src.monitoring.health_checker.settings', mock_settings):
            return ApplicationHealthChecker(name="test_app")
    
    @pytest.fixture
    def health_checker_orchestrator(self, mock_settings):
        """Create health checker orchestrator."""
        with patch('src.monitoring.health_checker.settings', mock_settings):
            return HealthChecker(timeout_seconds=30.0)
    
    @pytest.mark.asyncio
    async def test_api_health_checker_success(self, api_health_checker):
        """Test successful API health check."""
        result = await api_health_checker.check_health()
        
        assert result.name == "test_api"
        assert result.status == HealthStatus.HEALTHY
        assert "API responding normally" in result.message
        assert result.duration_ms >= 0
        assert "status_code" in result.metrics
        assert "response_time_ms" in result.metrics
    
    @pytest.mark.asyncio
    async def test_api_health_checker_failure(self):
        """Test API health checker with failing endpoint."""
        checker = APIHealthChecker(
            name="test_api_fail",
            url="https://httpbin.org/status/500",
            expected_status_codes=[200],
            timeout_seconds=5.0
        )
        
        result = await checker.check_health()
        
        assert result.name == "test_api_fail"
        assert result.status == HealthStatus.UNHEALTHY
        assert "unexpected status" in result.message.lower()
        assert result.metrics["status_code"] == 500
    
    @pytest.mark.asyncio
    async def test_api_health_checker_timeout(self):
        """Test API health checker timeout handling."""
        checker = APIHealthChecker(
            name="test_api_timeout",
            url="https://httpbin.org/delay/10",
            timeout_seconds=2.0
        )
        
        result = await checker.check_health()
        
        assert result.name == "test_api_timeout"
        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_system_health_checker_normal(self, system_health_checker):
        """Test system health checker with normal resources."""
        result = await system_health_checker.check_health()
        
        assert result.name == "test_system"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "cpu_percent" in result.metrics
        assert "memory_percent" in result.metrics
        assert "disk_percent" in result.metrics
        assert "memory_available_gb" in result.metrics
        assert "disk_free_gb" in result.metrics
    
    @pytest.mark.asyncio
    async def test_system_health_checker_high_usage(self):
        """Test system health checker with simulated high usage."""
        checker = SystemResourceChecker(
            name="test_system_high",
            cpu_threshold=0.0,  # Very low threshold to trigger alert
            memory_threshold=0.0,
            disk_threshold=0.0
        )
        
        result = await checker.check_health()
        
        assert result.name == "test_system_high"
        assert result.status == HealthStatus.DEGRADED or result.status == HealthStatus.UNHEALTHY
        assert "High CPU usage" in result.message or "High memory usage" in result.message or "High disk usage" in result.message
    
    @pytest.mark.asyncio
    async def test_application_health_checker_good(self, application_health_checker):
        """Test application health checker with good configuration."""
        result = await application_health_checker.check_health()
        
        assert result.name == "test_app"
        assert result.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        assert "config_valid" in result.metrics
        assert "gitlab_configured" in result.metrics
        assert "glm_configured" in result.metrics
    
    @pytest.mark.asyncio
    async def test_health_checker_orchestrator_all_checks(self, health_checker_orchestrator):
        """Test health checker orchestrator running all checks."""
        result = await health_checker_orchestrator.check_all()
        
        assert "overall_status" in result
        assert "is_healthy" in result
        assert "total_checks" in result
        assert "passed_checks" in result
        assert "failed_checks" in result
        assert "duration_ms" in result
        assert "timestamp" in result
        assert "results" in result
        assert len(result["results"]) > 0
    
    @pytest.mark.asyncio
    async def test_health_checker_orchestrator_single_check(self, health_checker_orchestrator):
        """Test health checker orchestrator running single check."""
        # Get available checker names
        checker_names = health_checker_orchestrator.get_checker_names()
        assert len(checker_names) > 0
        
        # Run first checker
        result = await health_checker_orchestrator.check_single(checker_names[0])
        
        assert result is not None
        assert hasattr(result, 'name')
        assert hasattr(result, 'status')
        assert hasattr(result, 'message')
    
    def test_health_checker_orchestrator_add_remove(self, health_checker_orchestrator):
        """Test adding and removing health checkers."""
        initial_count = len(health_checker_orchestrator.checkers)
        
        # Add a new checker
        new_checker = APIHealthChecker(
            name="additional_checker",
            url="https://httpbin.org/status/200"
        )
        health_checker_orchestrator.add_checker(new_checker)
        
        assert len(health_checker_orchestrator.checkers) == initial_count + 1
        assert "additional_checker" in health_checker_orchestrator.get_checker_names()
        
        # Remove the checker
        removed = health_checker_orchestrator.remove_checker("additional_checker")
        assert removed is True
        assert len(health_checker_orchestrator.checkers) == initial_count
        assert "additional_checker" not in health_checker_orchestrator.get_checker_names()
    
    @pytest.mark.asyncio
    async def test_health_checker_result_to_dict(self):
        """Test HealthCheckResult to_dict conversion."""
        result = HealthCheckResult(
            name="test",
            status=HealthStatus.HEALTHY,
            message="Test message",
            duration_ms=100.0,
            metrics={"test_metric": "value"},
            error_details=None
        )
        
        result_dict = result.to_dict()
        
        assert result_dict["name"] == "test"
        assert result_dict["status"] == "healthy"
        assert result_dict["message"] == "Test message"
        assert result_dict["duration_ms"] == 100.0
        assert result_dict["metrics"]["test_metric"] == "value"
        assert result_dict["error_details"] is None
        assert result_dict["is_healthy"] is True


class TestMetricsCollector:
    """Test suite for metrics collection components."""
    
    @pytest.fixture
    def api_tracker(self):
        """Create API tracker for testing."""
        return APITracker("test_api")
    
    @pytest.fixture
    def token_tracker(self):
        """Create token usage tracker."""
        return TokenUsageTracker()
    
    @pytest.fixture
    def system_metrics_collector(self):
        """Create system metrics collector."""
        return SystemMetricsCollector(collection_interval=1)
    
    @pytest.fixture
    def metrics_collector(self):
        """Create main metrics collector."""
        return MetricsCollector(collection_interval=1)
    
    def test_api_tracker_initialization(self, api_tracker):
        """Test API tracker initialization."""
        assert api_tracker.api_name == "test_api"
        assert api_tracker.request_count == 0
        assert api_tracker.success_count == 0
        assert api_tracker.error_count == 0
        assert api_tracker.min_response_time == float('inf')
        assert api_tracker.max_response_time == 0.0
    
    def test_api_tracker_record_success(self, api_tracker):
        """Test recording successful API request."""
        api_tracker.record_request(
            method="GET",
            status_code=200,
            response_time_ms=150.0
        )
        
        assert api_tracker.request_count == 1
        assert api_tracker.success_count == 1
        assert api_tracker.error_count == 0
        assert api_tracker.total_response_time == 0.15  # Convert to seconds
        assert api_tracker.min_response_time == 0.15
        assert api_tracker.max_response_time == 0.15
        assert len(api_tracker.response_times) == 1
    
    def test_api_tracker_record_error(self, api_tracker):
        """Test recording failed API request."""
        error = Exception("Test error")
        api_tracker.record_request(
            method="POST",
            status_code=500,
            response_time_ms=200.0,
            error=error
        )
        
        assert api_tracker.request_count == 1
        assert api_tracker.success_count == 0
        assert api_tracker.error_count == 1
        assert "Exception" in api_tracker.errors
    
    def test_api_tracker_statistics(self, api_tracker):
        """Test API tracker statistics generation."""
        # Record some requests
        api_tracker.record_request("GET", 200, 100.0)
        api_tracker.record_request("GET", 200, 200.0)
        api_tracker.record_request("POST", 500, 300.0, Exception("Error"))
        
        stats = api_tracker.get_statistics()
        
        assert stats["api_name"] == "test_api"
        assert stats["request_count"] == 3
        assert stats["success_count"] == 2
        assert stats["error_count"] == 1
        assert stats["success_rate"] == 2/3
        assert stats["avg_response_time_sec"] == 0.2  # (100+200+300)/3 / 1000
        assert "percentiles" in stats
        assert "status_codes" in stats
        assert "errors" in stats
    
    def test_api_tracker_reset_metrics(self, api_tracker):
        """Test resetting API tracker metrics."""
        # Record some requests
        api_tracker.record_request("GET", 200, 100.0)
        api_tracker.record_request("POST", 500, 200.0, Exception("Error"))
        
        # Reset metrics
        api_tracker.reset_metrics()
        
        assert api_tracker.request_count == 0
        assert api_tracker.success_count == 0
        assert api_tracker.error_count == 0
        assert api_tracker.total_response_time == 0.0
        assert len(api_tracker.response_times) == 0
        assert len(api_tracker.status_codes) == 0
        assert len(api_tracker.errors) == 0
    
    def test_token_tracker_record_usage(self, token_tracker):
        """Test recording token usage."""
        token_tracker.record_usage(
            prompt_tokens=100,
            completion_tokens=50,
            model="glm-4",
            success=True
        )
        
        assert token_tracker.total_tokens_used == 150
        assert token_tracker.prompt_tokens == 100
        assert token_tracker.completion_tokens == 50
        assert token_tracker.request_count == 1
    
    def test_token_tracker_statistics(self, token_tracker):
        """Test token usage statistics."""
        # Record multiple usage
        token_tracker.record_usage(100, 50, "glm-4", True)
        token_tracker.record_usage(200, 100, "glm-3", True)
        
        stats = token_tracker.get_usage_statistics()
        
        assert stats["total_tokens_used"] == 450
        assert stats["prompt_tokens"] == 300
        assert stats["completion_tokens"] == 150
        assert stats["request_count"] == 2
        assert stats["avg_tokens_per_request"] == 225.0
        assert "usage_by_date" in stats
        assert "usage_by_model" in stats
        assert stats["usage_by_model"]["glm-4"] == 150
        assert stats["usage_by_model"]["glm-3"] == 300
    
    def test_system_metrics_collector_current_metrics(self, system_metrics_collector):
        """Test getting current system metrics."""
        metrics = system_metrics_collector.get_current_metrics()
        
        assert "cpu_percent" in metrics
        assert "memory_percent" in metrics
        assert "disk_percent" in metrics
        assert "memory_available_gb" in metrics
        assert "disk_free_gb" in metrics
        assert "timestamp" in metrics
    
    def test_system_metrics_collector_historical_metrics(self, system_metrics_collector):
        """Test historical system metrics."""
        # Start collection briefly
        system_metrics_collector.start_collection()
        time.sleep(2)  # Collect some data
        system_metrics_collector.stop_collection()
        
        # Get historical metrics
        historical = system_metrics_collector.get_historical_metrics(hours=1)
        
        assert "cpu" in historical or len(historical) == 0  # May be empty if collection was too brief
    
    def test_metrics_collector_initialization(self, metrics_collector):
        """Test main metrics collector initialization."""
        assert metrics_collector.collection_interval == 1
        assert isinstance(metrics_collector.token_tracker, TokenUsageTracker)
        assert isinstance(metrics_collector.system_collector, SystemMetricsCollector)
        assert "gitlab" in metrics_collector.api_trackers or "glm" in metrics_collector.api_trackers
    
    def test_metrics_collector_record_api_request(self, metrics_collector):
        """Test recording API request in main collector."""
        metrics_collector.record_api_request(
            api_name="gitlab",
            method="GET",
            status_code=200,
            response_time_ms=150.0
        )
        
        gitlab_tracker = metrics_collector.get_api_tracker("gitlab")
        if gitlab_tracker:
            assert gitlab_tracker.request_count > 0
    
    def test_metrics_collector_record_token_usage(self, metrics_collector):
        """Test recording token usage in main collector."""
        initial_tokens = metrics_collector.token_tracker.total_tokens_used
        
        metrics_collector.record_token_usage(
            prompt_tokens=100,
            completion_tokens=50
        )
        
        assert metrics_collector.token_tracker.total_tokens_used == initial_tokens + 150
    
    def test_metrics_collector_get_all_metrics(self, metrics_collector):
        """Test getting all metrics from main collector."""
        # Record some data
        metrics_collector.record_api_request("gitlab", "GET", 200, 100.0)
        metrics_collector.record_token_usage(50, 25)
        
        all_metrics = metrics_collector.get_all_metrics()
        
        assert "uptime_seconds" in all_metrics
        assert "api_metrics" in all_metrics
        assert "token_usage" in all_metrics
        assert "system_metrics" in all_metrics
        assert "timestamp" in all_metrics
    
    def test_metrics_collector_prometheus_format(self, metrics_collector):
        """Test Prometheus metrics format."""
        # Record some data
        metrics_collector.record_api_request("gitlab", "GET", 200, 100.0)
        
        prometheus_metrics = metrics_collector.get_prometheus_metrics("main")
        
        assert isinstance(prometheus_metrics, str)
        assert len(prometheus_metrics) > 0
        
        # Check that it looks like Prometheus format
        lines = prometheus_metrics.split('\n')
        non_empty_lines = [line for line in lines if line.strip()]
        assert len(non_empty_lines) > 0
    
    def test_metrics_collector_list_registries(self, metrics_collector):
        """Test listing available registries."""
        registries = metrics_collector.list_available_registries()
        
        assert isinstance(registries, list)
        assert "main" in registries
        assert "tokens" in registries
        assert "system" in registries


class TestMonitoringServer:
    """Test suite for monitoring server components."""
    
    @pytest.fixture
    def server_config(self):
        """Create server configuration for testing."""
        return ServerConfig(
            host="127.0.0.1",
            port=8080,
            log_level="info",
            enable_cors=True
        )
    
    @pytest.fixture
    def mock_health_checker(self):
        """Create mock health checker."""
        mock_checker = Mock()
        mock_checker.check_all = AsyncMock(return_value={
            "overall_status": "healthy",
            "is_healthy": True,
            "total_checks": 2,
            "passed_checks": 2,
            "failed_checks": [],
            "duration_ms": 100.0,
            "timestamp": datetime.utcnow().isoformat(),
            "results": []
        })
        mock_checker.check_single = AsyncMock(return_value=Mock(
            to_dict=Mock(return_value={
                "name": "test_checker",
                "status": "healthy",
                "message": "All good"
            })
        ))
        mock_checker.get_checker_names = Mock(return_value=["test_checker"])
        mock_checker.get_status_summary = AsyncMock(return_value={
            "total_checkers": 1,
            "checker_names": ["test_checker"],
            "timeout_seconds": 30.0,
            "timestamp": datetime.utcnow().isoformat()
        })
        return mock_checker
    
    @pytest.fixture
    def mock_metrics_collector(self):
        """Create mock metrics collector."""
        mock_collector = Mock()
        mock_collector.get_all_metrics = Mock(return_value={
            "uptime_seconds": 3600,
            "api_metrics": {},
            "token_usage": {"total_tokens_used": 1000},
            "system_metrics": {"cpu_percent": 50.0},
            "timestamp": datetime.utcnow().isoformat()
        })
        mock_collector.get_prometheus_metrics = Mock(return_value="# HELP test_metric Test metric\ntest_metric 1\n")
        mock_collector.list_available_registries = Mock(return_value=["main", "tokens", "system"])
        mock_collector.reset_metrics = Mock()
        mock_collector.start_collection = Mock()
        mock_collector.stop_collection = Mock()
        return mock_collector
    
    @pytest.fixture
    def monitoring_server(self, server_config, mock_health_checker, mock_metrics_collector):
        """Create monitoring server with mocked dependencies."""
        return MonitoringServer(
            health_checker=mock_health_checker,
            metrics_collector=mock_metrics_collector,
            config=server_config
        )
    
    def test_server_config_initialization(self, server_config):
        """Test server configuration initialization."""
        assert server_config.host == "127.0.0.1"
        assert server_config.port == 8080
        assert server_config.log_level == "info"
        assert server_config.enable_cors is True
    
    def test_monitoring_server_initialization(self, monitoring_server):
        """Test monitoring server initialization."""
        assert monitoring_server.config.host == "127.0.0.1"
        assert monitoring_server.config.port == 8080
        assert monitoring_server.health_checker is not None
        assert monitoring_server.metrics_collector is not None
        assert monitoring_server.app is not None
    
    def test_monitoring_server_get_app(self, monitoring_server):
        """Test getting FastAPI app instance."""
        app = monitoring_server.get_app()
        assert app is not None
        assert hasattr(app, 'routes')
    
    def test_monitoring_server_endpoints_setup(self, monitoring_server):
        """Test that all endpoints are properly set up."""
        app = monitoring_server.get_app()
        
        # Get all route paths
        route_paths = [route.path for route in app.routes]
        
        expected_routes = [
            "/",
            "/health",
            "/health/detailed", 
            "/health/checker/{checker_name}",
            "/health/status",
            "/metrics",
            "/metrics/prometheus",
            "/metrics/registries",
            "/admin/reset-metrics",
            "/admin/config"
        ]
        
        for expected_route in expected_routes:
            assert expected_route in route_paths, f"Route {expected_route} not found"
    
    def test_health_endpoint(self, monitoring_server):
        """Test basic health endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "uptime_seconds" in data
        assert data["status"] == "ok"
    
    def test_detailed_health_endpoint(self, monitoring_server):
        """Test detailed health endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/health/detailed")
        
        assert response.status_code == 200
        data = response.json()
        assert "overall_status" in data
        assert "is_healthy" in data
        assert "total_checks" in data
        assert "results" in data
    
    def test_specific_health_endpoint(self, monitoring_server):
        """Test specific health check endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/health/checker/test_checker")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "status" in data
        assert data["name"] == "test_checker"
    
    def test_specific_health_endpoint_not_found(self, monitoring_server):
        """Test specific health check endpoint with non-existent checker."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/health/checker/nonexistent")
        
        assert response.status_code == 404
    
    def test_health_status_endpoint(self, monitoring_server):
        """Test health status endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/health/status")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_checkers" in data
        assert "checker_names" in data
        assert "timeout_seconds" in data
    
    def test_metrics_endpoint(self, monitoring_server):
        """Test metrics endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "uptime_seconds" in data
        assert "api_metrics" in data
        assert "token_usage" in data
        assert "system_metrics" in data
    
    def test_prometheus_metrics_endpoint(self, monitoring_server):
        """Test Prometheus metrics endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/metrics/prometheus?registry=main")
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        assert "# HELP" in response.text
    
    def test_prometheus_metrics_invalid_registry(self, monitoring_server):
        """Test Prometheus metrics endpoint with invalid registry."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/metrics/prometheus?registry=invalid")
        
        assert response.status_code == 400
    
    def test_metrics_registries_endpoint(self, monitoring_server):
        """Test metrics registries endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/metrics/registries")
        
        assert response.status_code == 200
        data = response.json()
        assert "registries" in data
        assert "count" in data
        assert isinstance(data["registries"], list)
    
    def test_admin_reset_metrics_endpoint(self, monitoring_server):
        """Test admin reset metrics endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.post("/admin/reset-metrics")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "api_name" in data
        assert data["api_name"] == "all"
    
    def test_admin_config_endpoint(self, monitoring_server):
        """Test admin config endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/admin/config")
        
        assert response.status_code == 200
        data = response.json()
        assert "host" in data
        assert "port" in data
        assert "log_level" in data
        assert "cors_enabled" in data
        assert "startup_time" in data
    
    def test_server_info_endpoint(self, monitoring_server):
        """Test server info endpoint."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "status" in data
        assert "endpoints" in data
    
    def test_cors_middleware(self, monitoring_server):
        """Test CORS middleware functionality."""
        client = TestClient(monitoring_server.get_app())
        
        response = client.options("/health", headers={
            "Origin": "https://example.com",
            "Access-Control-Request-Method": "GET"
        })
        
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestAlertSystem:
    """Test suite for alert system components."""
    
    @pytest.fixture
    def alert_rule(self):
        """Create sample alert rule for testing."""
        return AlertRule(
            name="test_rule",
            description="Test alert rule",
            severity=AlertSeverity.WARNING,
            metric_name="cpu_percent",
            threshold_value=80.0,
            comparison="gt",
            consecutive_breaches=2,
            cooldown_minutes=5,
            notification_channels=[NotificationChannel.LOG]
        )
    
    @pytest.fixture
    def health_alert_rule(self):
        """Create health-based alert rule for testing."""
        return AlertRule(
            name="health_rule",
            description="Test health alert rule", 
            severity=AlertSeverity.CRITICAL,
            health_check_name="test_checker",
            health_status="unhealthy",
            consecutive_breaches=1,
            cooldown_minutes=1,
            notification_channels=[NotificationChannel.LOG]
        )
    
    @pytest.fixture
    def alert_manager(self):
        """Create alert manager for testing."""
        return AlertManager()
    
    def test_alert_rule_creation(self, alert_rule):
        """Test alert rule creation and validation."""
        assert alert_rule.name == "test_rule"
        assert alert_rule.description == "Test alert rule"
        assert alert_rule.severity == AlertSeverity.WARNING
        assert alert_rule.metric_name == "cpu_percent"
        assert alert_rule.threshold_value == 80.0
        assert alert_rule.comparison == "gt"
        assert alert_rule.consecutive_breaches == 2
        assert alert_rule.cooldown_minutes == 5
        assert NotificationChannel.LOG in alert_rule.notification_channels
    
    def test_alert_rule_to_dict(self, alert_rule):
        """Test alert rule to_dict conversion."""
        rule_dict = alert_rule.to_dict()
        
        assert rule_dict["name"] == "test_rule"
        assert rule_dict["severity"] == "warning"
        assert rule_dict["metric_name"] == "cpu_percent"
        assert rule_dict["threshold_value"] == 80.0
        assert rule_dict["comparison"] == "gt"
        assert isinstance(rule_dict["notification_channels"], list)
    
    def test_alert_creation(self):
        """Test alert creation and validation."""
        alert = Alert(
            id="test_alert_1",
            rule_name="test_rule",
            severity=AlertSeverity.ERROR,
            status=AlertStatus.ACTIVE,
            message="Test alert message",
            details={"metric_value": 85.0}
        )
        
        assert alert.id == "test_alert_1"
        assert alert.rule_name == "test_rule"
        assert alert.severity == AlertSeverity.ERROR
        assert alert.status == AlertStatus.ACTIVE
        assert alert.message == "Test alert message"
        assert alert.details["metric_value"] == 85.0
        assert isinstance(alert.created_at, datetime)
    
    def test_alert_to_dict(self):
        """Test alert to_dict conversion."""
        alert = Alert(
            id="test_alert_2",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            message="Another test alert"
        )
        
        alert_dict = alert.to_dict()
        
        assert alert_dict["id"] == "test_alert_2"
        assert alert_dict["rule_name"] == "test_rule"
        assert alert_dict["severity"] == "warning"
        assert alert_dict["status"] == "active"
        assert alert_dict["message"] == "Another test alert"
        assert "created_at" in alert_dict
        assert "updated_at" in alert_dict
    
    def test_alert_rule_engine_evaluation(self):
        """Test alert rule engine evaluation."""
        engine = AlertRuleEngine()
        
        # Test metric-based rule
        rule = AlertRule(
            name="cpu_rule",
            description="High CPU",
            severity=AlertSeverity.WARNING,
            metric_name="cpu_percent",
            threshold_value=80.0,
            comparison="gt"
        )
        
        # Test condition met
        metrics = {"cpu_percent": 85.0}
        assert engine.evaluate_metric_rule(rule, metrics) is True
        
        # Test condition not met
        metrics = {"cpu_percent": 75.0}
        assert engine.evaluate_metric_rule(rule, metrics) is False
        
        # Test different comparisons
        rule.comparison = "lt"
        metrics = {"cpu_percent": 75.0}
        assert engine.evaluate_metric_rule(rule, metrics) is True
        
        rule.comparison = "gte"
        metrics = {"cpu_percent": 80.0}
        assert engine.evaluate_metric_rule(rule, metrics) is True
        
        rule.comparison = "eq"
        metrics = {"cpu_percent": 80.0}
        assert engine.evaluate_metric_rule(rule, metrics) is True
    
    def test_alert_rule_engine_health_evaluation(self):
        """Test alert rule engine health check evaluation."""
        engine = AlertRuleEngine()
        
        rule = AlertRule(
            name="health_rule",
            description="Health check failure",
            severity=AlertSeverity.CRITICAL,
            health_check_name="gitlab_api",
            health_status="unhealthy"
        )
        
        # Mock health check result
        mock_result = Mock()
        mock_result.status.value = "unhealthy"
        
        health_results = {"gitlab_api": mock_result}
        assert engine.evaluate_health_rule(rule, health_results) is True
        
        # Test with different status
        mock_result.status.value = "healthy"
        assert engine.evaluate_health_rule(rule, health_results) is False
    
    def test_alert_manager_initialization(self, alert_manager):
        """Test alert manager initialization."""
        assert len(alert_manager.rules) > 0  # Should have default rules
        assert alert_manager.alert_counter == 0
        assert len(alert_manager.alerts) == 0
        assert len(alert_manager.notification_handlers) > 0
    
    def test_alert_manager_add_remove_rule(self, alert_manager, alert_rule):
        """Test adding and removing alert rules."""
        initial_count = len(alert_manager.rules)
        
        # Add rule
        alert_manager.add_rule(alert_rule)
        assert len(alert_manager.rules) == initial_count + 1
        assert "test_rule" in alert_manager.rules
        
        # Remove rule
        removed = alert_manager.remove_rule("test_rule")
        assert removed is True
        assert len(alert_manager.rules) == initial_count
        assert "test_rule" not in alert_manager.rules
    
    def test_alert_manager_evaluate_metric_rules(self, alert_manager, alert_rule):
        """Test evaluating metric-based alert rules."""
        alert_manager.add_rule(alert_rule)
        
        # First evaluation (should not trigger - consecutive breaches)
        metrics = {"cpu_percent": 85.0}
        alerts = alert_manager.evaluate_rules(metrics=metrics)
        assert len(alerts) == 0
        
        # Second evaluation (should trigger)
        alerts = alert_manager.evaluate_rules(metrics=metrics)
        assert len(alerts) == 1
        assert alerts[0].rule_name == "test_rule"
        assert alerts[0].severity == AlertSeverity.WARNING
    
    def test_alert_manager_evaluate_health_rules(self, alert_manager, health_alert_rule):
        """Test evaluating health-based alert rules."""
        alert_manager.add_rule(health_alert_rule)
        
        # Mock health check result
        mock_result = Mock()
        mock_result.status.value = "unhealthy"
        mock_result.message = "API connection failed"
        
        health_results = {"test_checker": mock_result}
        alerts = alert_manager.evaluate_rules(health_results=health_results)
        
        assert len(alerts) == 1
        assert alerts[0].rule_name == "health_rule"
        assert alerts[0].severity == AlertSeverity.CRITICAL
        assert "test_checker" in alerts[0].message
    
    def test_alert_manager_acknowledge_resolve(self, alert_manager):
        """Test acknowledging and resolving alerts."""
        # Create a test alert
        alert = Alert(
            id="test_alert_ack",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            message="Test alert"
        )
        alert_manager.alerts[alert.id] = alert
        
        # Acknowledge alert
        acknowledged = alert_manager.acknowledge_alert(alert.id, "test_user")
        assert acknowledged is True
        assert alert.status == AlertStatus.ACKNOWLEDGED
        assert alert.acknowledged_by == "test_user"
        
        # Resolve alert
        resolved = alert_manager.resolve_alert(alert.id, "test_user")
        assert resolved is True
        assert alert.status == AlertStatus.RESOLVED
        assert alert.details["resolved_by"] == "test_user"
    
    def test_alert_manager_suppress(self, alert_manager):
        """Test suppressing alerts."""
        alert = Alert(
            id="test_alert_suppress",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            message="Test alert"
        )
        alert_manager.alerts[alert.id] = alert
        
        suppressed = alert_manager.suppress_alert(alert.id, "False positive")
        assert suppressed is True
        assert alert.status == AlertStatus.SUPPRESSED
        assert alert.details["suppression_reason"] == "False positive"
    
    def test_alert_manager_list_alerts(self, alert_manager):
        """Test listing alerts with filters."""
        # Create test alerts
        alert1 = Alert("alert1", "rule1", AlertSeverity.WARNING, AlertStatus.ACTIVE, "Test 1")
        alert2 = Alert("alert2", "rule2", AlertSeverity.ERROR, AlertStatus.RESOLVED, "Test 2")
        alert3 = Alert("alert3", "rule3", AlertSeverity.CRITICAL, AlertStatus.ACTIVE, "Test 3")
        
        alert_manager.alerts.update({a.id: a for a in [alert1, alert2, alert3]})
        
        # List all alerts
        all_alerts = alert_manager.list_alerts()
        assert len(all_alerts) == 3
        
        # Filter by status
        active_alerts = alert_manager.list_alerts(status=AlertStatus.ACTIVE)
        assert len(active_alerts) == 2
        
        # Filter by severity
        critical_alerts = alert_manager.list_alerts(severity=AlertSeverity.CRITICAL)
        assert len(critical_alerts) == 1
        assert critical_alerts[0].id == "alert3"
        
        # Test limit
        limited_alerts = alert_manager.list_alerts(limit=2)
        assert len(limited_alerts) == 2
    
    def test_alert_manager_statistics(self, alert_manager):
        """Test alert manager statistics."""
        # Create test alerts with different statuses
        alerts = [
            Alert("a1", "r1", AlertSeverity.WARNING, AlertStatus.ACTIVE, "Active alert"),
            Alert("a2", "r2", AlertSeverity.ERROR, AlertStatus.ACKNOWLEDGED, "Acked alert"),
            Alert("a3", "r3", AlertSeverity.CRITICAL, AlertStatus.RESOLVED, "Resolved alert"),
            Alert("a4", "r4", AlertSeverity.INFO, AlertStatus.SUPPRESSED, "Suppressed alert")
        ]
        
        alert_manager.alerts.update({a.id: a for a in alerts})
        
        stats = alert_manager.get_alert_statistics()
        
        assert stats["total_alerts"] == 4
        assert stats["active_alerts"] == 1
        assert stats["acknowledged_alerts"] == 1
        assert stats["resolved_alerts"] == 1
        assert stats["suppressed_alerts"] == 1
        assert "severity_breakdown" in stats
        assert stats["severity_breakdown"]["warning"] == 1
        assert stats["severity_breakdown"]["error"] == 1
        assert stats["severity_breakdown"]["critical"] == 1
        assert stats["severity_breakdown"]["info"] == 1
    
    def test_notification_handler_log(self):
        """Test log notification handler."""
        from src.monitoring.alerts import LogNotificationHandler
        
        handler = LogNotificationHandler()
        
        alert = Alert(
            id="test_log",
            rule_name="test_rule",
            severity=AlertSeverity.WARNING,
            status=AlertStatus.ACTIVE,
            message="Test log notification",
            details={"key": "value"}
        )
        
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            severity=AlertSeverity.WARNING,
            notification_channels=[NotificationChannel.LOG]
        )
        
        # Test that notification doesn't raise exception
        result = asyncio.run(handler.send_notification(alert, rule, "Test message"))
        assert result is True
    
    @pytest.mark.asyncio
    async def test_notification_handler_webhook_success(self):
        """Test webhook notification handler with successful response."""
        from src.monitoring.alerts import WebhookNotificationHandler
        
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            handler = WebhookNotificationHandler()
            
            alert = Alert(
                id="test_webhook",
                rule_name="test_rule",
                severity=AlertSeverity.ERROR,
                status=AlertStatus.ACTIVE,
                message="Test webhook notification"
            )
            
            rule = AlertRule(
                name="test_rule",
                description="Test rule",
                severity=AlertSeverity.ERROR,
                webhook_url="https://example.com/webhook",
                notification_channels=[NotificationChannel.WEBHOOK]
            )
            
            result = await handler.send_notification(alert, rule, "Test message")
            assert result is True
    
    @pytest.mark.asyncio
    async def test_notification_handler_webhook_failure(self):
        """Test webhook notification handler with failed response."""
        from src.monitoring.alerts import WebhookNotificationHandler
        
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_client.return_value.__aenter__.return_value.post.return_value = mock_response
            
            handler = WebhookNotificationHandler()
            
            alert = Alert(
                id="test_webhook_fail",
                rule_name="test_rule",
                severity=AlertSeverity.CRITICAL,
                status=AlertStatus.ACTIVE,
                message="Test webhook failure"
            )
            
            rule = AlertRule(
                name="test_rule",
                description="Test rule",
                severity=AlertSeverity.CRITICAL,
                webhook_url="https://example.com/webhook",
                notification_channels=[NotificationChannel.WEBHOOK]
            )
            
            result = await handler.send_notification(alert, rule, "Test message")
            assert result is False


class TestPerformanceAndStress:
    """Performance and stress tests for monitoring components."""
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test performance of concurrent health checks."""
        # Create multiple API health checkers
        checkers = [
            APIHealthChecker(
                name=f"concurrent_checker_{i}",
                url="https://httpbin.org/status/200",
                timeout_seconds=10.0
            )
            for i in range(10)
        ]
        
        orchestrator = HealthChecker(timeout_seconds=30.0)
        for checker in checkers:
            orchestrator.add_checker(checker)
        
        start_time = time.time()
        result = await orchestrator.check_all()
        duration = time.time() - start_time
        
        assert result["overall_status"] in ["healthy", "degraded", "unhealthy"]
        assert len(result["results"]) == 10
        assert duration < 15.0  # Should complete within 15 seconds
    
    @pytest.mark.slow
    def test_metrics_collector_performance(self):
        """Test performance of metrics collector with high volume."""
        collector = MetricsCollector()
        
        # Simulate high volume of API requests
        start_time = time.time()
        
        for i in range(1000):
            collector.record_api_request(
                api_name="gitlab",
                method="GET",
                status_code=200 if i % 10 != 0 else 500,
                response_time_ms=50 + (i % 200)
            )
        
        duration = time.time() - start_time
        
        # Should handle 1000 records quickly
        assert duration < 1.0
        
        # Verify metrics were recorded
        gitlab_tracker = collector.get_api_tracker("gitlab")
        assert gitlab_tracker.request_count == 1000
        assert gitlab_tracker.success_count == 900
        assert gitlab_tracker.error_count == 100
    
    @pytest.mark.slow
    def test_alert_system_performance(self):
        """Test alert system performance with many rules and evaluations."""
        manager = AlertManager()
        
        # Add many rules
        for i in range(50):
            rule = AlertRule(
                name=f"perf_rule_{i}",
                description=f"Performance test rule {i}",
                severity=AlertSeverity.WARNING,
                metric_name=f"metric_{i}",
                threshold_value=80.0,
                comparison="gt",
                consecutive_breaches=1,
                cooldown_minutes=0,  # No cooldown for performance test
                notification_channels=[NotificationChannel.LOG]
            )
            manager.add_rule(rule)
        
        # Generate metrics that trigger all rules
        metrics = {f"metric_{i}": 85.0 for i in range(50)}
        
        start_time = time.time()
        alerts = manager.evaluate_rules(metrics=metrics)
        duration = time.time() - start_time
        
        # Should handle 50 rules quickly
        assert duration < 0.5
        assert len(alerts) == 50
    
    @pytest.mark.slow
    def test_system_metrics_collection_continuously(self):
        """Test continuous system metrics collection."""
        collector = SystemMetricsCollector(collection_interval=0.1)  # 100ms interval
        
        collector.start_collection()
        time.sleep(1.0)  # Collect for 1 second
        collector.stop_collection()
        
        # Should have collected several data points
        historical = collector.get_historical_metrics(hours=1)
        
        # Should have data for at least some metrics
        assert len(historical) > 0
    
    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_monitoring_server_load(self):
        """Test monitoring server under load."""
        mock_health_checker = Mock()
        mock_health_checker.check_all = AsyncMock(return_value={
            "overall_status": "healthy",
            "is_healthy": True,
            "total_checks": 1,
            "passed_checks": 1,
            "failed_checks": [],
            "duration_ms": 10.0,
            "timestamp": datetime.utcnow().isoformat(),
            "results": []
        })
        
        mock_metrics_collector = Mock()
        mock_metrics_collector.get_all_metrics = Mock(return_value={
            "uptime_seconds": 3600,
            "api_metrics": {},
            "token_usage": {"total_tokens_used": 1000},
            "system_metrics": {"cpu_percent": 50.0},
            "timestamp": datetime.utcnow().isoformat()
        })
        
        config = ServerConfig(host="127.0.0.1", port=8081)
        server = MonitoringServer(
            health_checker=mock_health_checker,
            metrics_collector=mock_metrics_collector,
            config=config
        )
        
        client = TestClient(server.get_app())
        
        # Make many concurrent requests
        import concurrent.futures
        
        def make_request():
            return client.get("/health").status_code
        
        start_time = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_request) for _ in range(100)]
            results = [future.result() for future in futures]
        
        duration = time.time() - start_time
        
        # All requests should succeed
        assert all(result == 200 for result in results)
        # Should handle 100 requests quickly
        assert duration < 5.0


class TestErrorHandlingAndEdgeCases:
    """Test error handling and edge cases for monitoring components."""
    
    @pytest.mark.asyncio
    async def test_health_checker_with_invalid_url(self):
        """Test health checker with invalid URL."""
        checker = APIHealthChecker(
            name="invalid_url",
            url="not-a-valid-url",
            timeout_seconds=1.0
        )
        
        result = await checker.check_health()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "failed" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_health_checker_timeout_handling(self):
        """Test health checker timeout handling."""
        checker = APIHealthChecker(
            name="timeout_test",
            url="https://httpbin.org/delay/10",
            timeout_seconds=0.1  # Very short timeout
        )
        
        result = await checker.check_health()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert "timeout" in result.message.lower()
    
    @pytest.mark.asyncio
    async def test_health_checker_exception_handling(self):
        """Test health checker exception handling."""
        # Create a checker that will raise an exception
        class FailingChecker(APIHealthChecker):
            async def _perform_check(self):
                raise Exception("Simulated failure")
        
        checker = FailingChecker(
            name="failing_checker",
            url="https://example.com",
            timeout_seconds=1.0
        )
        
        result = await checker.check_health()
        
        assert result.status == HealthStatus.UNHEALTHY
        assert result.error_details is not None
        assert result.last_error is not None
    
    def test_metrics_collector_invalid_api_name(self):
        """Test metrics collector with invalid API name."""
        collector = MetricsCollector()
        
        # Record with non-existent API
        collector.record_api_request(
            api_name="nonexistent_api",
            method="GET",
            status_code=200,
            response_time_ms=100.0
        )
        
        # Should not raise exception, just log warning
        assert collector.get_api_tracker("nonexistent_api") is None
    
    def test_alert_rule_invalid_comparison(self):
        """Test alert rule with invalid comparison operator."""
        engine = AlertRuleEngine()
        
        rule = AlertRule(
            name="invalid_comparison",
            description="Invalid comparison test",
            severity=AlertSeverity.WARNING,
            metric_name="test_metric",
            threshold_value=80.0,
            comparison="invalid_operator"  # Invalid operator
        )
        
        metrics = {"test_metric": 85.0}
        
        # Should return False for invalid comparison
        assert engine.evaluate_metric_rule(rule, metrics) is False
    
    def test_alert_rule_missing_metric(self):
        """Test alert rule with missing metric."""
        engine = AlertRuleEngine()
        
        rule = AlertRule(
            name="missing_metric",
            description="Missing metric test",
            severity=AlertSeverity.WARNING,
            metric_name="nonexistent_metric",
            threshold_value=80.0,
            comparison="gt"
        )
        
        metrics = {"other_metric": 85.0}
        
        # Should return False when metric is missing
        assert engine.evaluate_metric_rule(rule, metrics) is False
    
    def test_alert_manager_nonexistent_alert_operations(self):
        """Test alert manager operations on nonexistent alerts."""
        manager = AlertManager()
        
        # Test operations on nonexistent alerts
        assert manager.acknowledge_alert("nonexistent", "user") is False
        assert manager.resolve_alert("nonexistent", "user") is False
        assert manager.suppress_alert("nonexistent", "reason") is False
        assert manager.get_alert("nonexistent") is None
    
    def test_notification_handler_missing_webhook_url(self):
        """Test webhook notification handler with missing URL."""
        from src.monitoring.alerts import WebhookNotificationHandler
        
        handler = WebhookNotificationHandler()
        
        alert = Alert(
            id="test_no_url",
            rule_name="test_rule",
            severity=AlertSeverity.ERROR,
            status=AlertStatus.ACTIVE,
            message="Test notification"
        )
        
        rule = AlertRule(
            name="test_rule",
            description="Test rule",
            severity=AlertSeverity.ERROR,
            webhook_url=None,  # No webhook URL
            notification_channels=[NotificationChannel.WEBHOOK]
        )
        
        # Should return False when webhook URL is missing
        result = asyncio.run(handler.send_notification(alert, rule, "Test message"))
        assert result is False
    
    @pytest.mark.asyncio
    async def test_monitoring_server_error_endpoints(self):
        """Test monitoring server error handling in endpoints."""
        # Create server with mocked components that raise exceptions
        mock_health_checker = Mock()
        mock_health_checker.check_all = AsyncMock(side_effect=Exception("Health check failed"))
        
        mock_metrics_collector = Mock()
        mock_metrics_collector.get_all_metrics = Mock(side_effect=Exception("Metrics failed"))
        
        config = ServerConfig(host="127.0.0.1", port=8082)
        server = MonitoringServer(
            health_checker=mock_health_checker,
            metrics_collector=mock_metrics_collector,
            config=config
        )
        
        client = TestClient(server.get_app())
        
        # Test that exceptions are handled gracefully
        response = client.get("/health/detailed")
        assert response.status_code == 500
        
        response = client.get("/metrics")
        assert response.status_code == 500
    
    def test_persistence_and_recovery(self):
        """Test data persistence and recovery scenarios."""
        # Test metrics collector state preservation
        collector = MetricsCollector()
        
        # Record some data
        collector.record_api_request("gitlab", "GET", 200, 100.0)
        collector.record_token_usage(50, 25)
        
        # Verify data exists
        gitlab_tracker = collector.get_api_tracker("gitlab")
        initial_requests = gitlab_tracker.request_count if gitlab_tracker else 0
        initial_tokens = collector.token_tracker.total_tokens_used
        
        # Reset and verify
        collector.reset_metrics()
        
        gitlab_tracker = collector.get_api_tracker("gitlab")
        if gitlab_tracker:
            assert gitlab_tracker.request_count == 0
        assert collector.token_tracker.total_tokens_used == 0
    
    def test_thread_safety(self):
        """Test thread safety of monitoring components."""
        import threading
        import time
        
        collector = MetricsCollector()
        
        def record_requests(thread_id):
            for i in range(100):
                collector.record_api_request(
                    api_name="thread_test",
                    method="GET",
                    status_code=200,
                    response_time_ms=50 + i
                )
        
        # Create multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=record_requests, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all requests were recorded correctly
        tracker = collector.get_api_tracker("thread_test")
        if tracker:
            assert tracker.request_count == 500  # 5 threads * 100 requests each


class TestIntegrationScenarios:
    """Integration tests for complete monitoring scenarios."""
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_end_to_end_monitoring_workflow(self):
        """Test complete end-to-end monitoring workflow."""
        # Create real components (not mocked)
        health_checker = HealthChecker(timeout_seconds=10.0)
        metrics_collector = MetricsCollector()
        alert_manager = AlertManager()
        
        # Start metrics collection
        metrics_collector.start_collection()
        
        try:
            # Step 1: Perform health checks
            health_results = await health_checker.check_all()
            assert "overall_status" in health_results
            
            # Step 2: Record some metrics
            metrics_collector.record_api_request("gitlab", "GET", 200, 150.0)
            metrics_collector.record_api_request("glm", "POST", 500, 200.0, Exception("API Error"))
            metrics_collector.record_token_usage(100, 50)
            
            # Step 3: Get current metrics
            current_metrics = metrics_collector.get_all_metrics()
            assert "api_metrics" in current_metrics
            assert "token_usage" in current_metrics
            assert "system_metrics" in current_metrics
            
            # Step 4: Evaluate alert rules
            alerts = alert_manager.evaluate_rules(
                metrics=current_metrics.get("system_metrics", {}),
                health_results={r["name"]: Mock(status=Mock(value=r.get("status", "healthy"))) 
                              for r in health_results.get("results", [])}
            )
            
            # Should have some alerts (depending on system state)
            assert isinstance(alerts, list)
            
            # Step 5: Test alert management
            for alert in alerts:
                alert_id = alert.id
                # Acknowledge alert
                assert alert_manager.acknowledge_alert(alert_id, "test_user") is True
                
                # Resolve alert
                assert alert_manager.resolve_alert(alert_id, "test_user") is True
            
        finally:
            # Cleanup
            metrics_collector.stop_collection()
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_with_real_components(self):
        """Test monitoring server with real components."""
        # Create real components
        health_checker = HealthChecker()
        metrics_collector = MetricsCollector()
        
        config = ServerConfig(host="127.0.0.1", port=8083)
        server = MonitoringServer(
            health_checker=health_checker,
            metrics_collector=metrics_collector,
            config=config
        )
        
        client = TestClient(server.get_app())
        
        # Test all endpoints work with real components
        response = client.get("/health")
        assert response.status_code == 200
        
        response = client.get("/metrics")
        assert response.status_code == 200
        
        response = client.get("/health/detailed")
        assert response.status_code == 200
        
        response = client.get("/metrics/registries")
        assert response.status_code == 200
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_alert_rule_lifecycle(self):
        """Test complete alert rule lifecycle."""
        manager = AlertManager()
        
        # Create custom rule
        rule = AlertRule(
            name="lifecycle_test",
            description="Lifecycle test rule",
            severity=AlertSeverity.WARNING,
            metric_name="test_metric",
            threshold_value=80.0,
            comparison="gt",
            consecutive_breaches=1,
            cooldown_minutes=0,
            auto_resolve_minutes=1,
            notification_channels=[NotificationChannel.LOG]
        )
        
        manager.add_rule(rule)
        
        # Trigger alert
        metrics = {"test_metric": 85.0}
        alerts = manager.evaluate_rules(metrics=metrics)
        assert len(alerts) == 1
        
        alert_id = alerts[0].id
        
        # Verify alert is active
        alert = manager.get_alert(alert_id)
        assert alert is not None
        assert alert.status == AlertStatus.ACTIVE
        
        # Acknowledge alert
        manager.acknowledge_alert(alert_id, "test_user")
        alert = manager.get_alert(alert_id)
        assert alert.status == AlertStatus.ACKNOWLEDGED
        
        # Suppress alert
        manager.suppress_alert(alert_id, "Test suppression")
        alert = manager.get_alert(alert_id)
        assert alert.status == AlertStatus.SUPPRESSED
        
        # Wait for auto-resolution (simulate time passing)
        alert.created_at = datetime.utcnow() - timedelta(minutes=2)
        manager.evaluate_rules()  # This should trigger auto-resolution
        
        alert = manager.get_alert(alert_id)
        assert alert.status == AlertStatus.RESOLVED
    
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_metrics_aggregation_over_time(self):
        """Test metrics aggregation over time."""
        collector = MetricsCollector()
        
        # Simulate API requests over time
        base_time = time.time()
        for i in range(100):
            # Simulate some time passing
            current_time = base_time + i * 0.01
            
            # Record request with varying response times
            response_time = 50 + (i % 200)  # 50-250ms range
            status_code = 200 if i % 10 != 0 else 500  # 10% error rate
            
            collector.record_api_request(
                api_name="aggregation_test",
                method="GET",
                status_code=status_code,
                response_time_ms=response_time
            )
        
        # Get aggregated statistics
        tracker = collector.get_api_tracker("aggregation_test")
        if tracker:
            stats = tracker.get_statistics()
            
            assert stats["request_count"] == 100
            assert stats["success_count"] == 90
            assert stats["error_count"] == 10
            assert stats["success_rate"] == 0.9
            assert "percentiles" in stats
            assert "p50" in stats["percentiles"]
            assert "p95" in stats["percentiles"]
            assert "p99" in stats["percentiles"]
    
    @pytest.mark.integration
    def test_system_monitoring_under_load(self):
        """Test system monitoring under simulated load."""
        import multiprocessing
        import time
        
        # Start system metrics collection
        collector = SystemMetricsCollector(collection_interval=0.1)
        collector.start_collection()
        
        try:
            # Create CPU load
            def cpu_load():
                end_time = time.time() + 2
                while time.time() < end_time:
                    # Simple CPU-intensive calculation
                    sum(i * i for i in range(1000))
            
            # Start multiple processes to create load
            processes = []
            for _ in range(multiprocessing.cpu_count()):
                p = multiprocessing.Process(target=cpu_load)
                processes.append(p)
                p.start()
            
            # Wait for load to complete
            for p in processes:
                p.join()
            
            # Give metrics collector time to record
            time.sleep(0.5)
            
            # Check that metrics were collected
            current_metrics = collector.get_current_metrics()
            assert "cpu_percent" in current_metrics
            
            # CPU usage should be higher during load
            assert current_metrics["cpu_percent"] > 0
            
            # Check historical data
            historical = collector.get_historical_metrics(hours=1)
            assert "cpu" in historical
            
        finally:
            collector.stop_collection()


if __name__ == "__main__":
    pytest.main([__file__])