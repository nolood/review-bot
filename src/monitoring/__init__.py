"""
Monitoring module for GLM Code Review Bot.

This module provides comprehensive monitoring capabilities including:
- Health checks for external dependencies and system resources
- Prometheus metrics collection for API performance and usage
- FastAPI-based monitoring server with health and metrics endpoints
- Alerting system with configurable rules and notifications

Architecture:
- Clean architecture with dependency injection
- Async/await patterns for I/O operations
- Integration with existing settings, exceptions, and logging
- Type-safe implementations with comprehensive error handling

Components:
- health_checker: Health check implementations
- metrics_collector: Prometheus metrics collection
- monitoring_server: FastAPI server for endpoints
- alerts: Alerting rules and notification system
"""

# Import all monitoring components
from .health_checker import HealthChecker, HealthStatus, HealthCheckResult
from .metrics_collector import MetricsCollector
from .monitoring_server import MonitoringServer
from .alerts import AlertManager, AlertRule, AlertSeverity, AlertStatus

__all__ = [
    "HealthChecker",
    "HealthStatus", 
    "HealthCheckResult",
    "MetricsCollector",
    "MonitoringServer",
    "AlertManager",
    "AlertRule",
    "AlertSeverity",
    "AlertStatus",
]