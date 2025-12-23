"""
Alerting system for GLM Code Review Bot monitoring.

This module provides comprehensive alerting capabilities including:
- Configurable alert rules with thresholds and conditions
- Multiple alert notification channels (logs, webhooks, etc.)
- Alert lifecycle management (trigger, ack, resolve)
- Alert aggregation and rate limiting

Features:
- Clean async/await architecture for notifications
- Configurable alert rules with flexible conditions
- Support for multiple notification channels
- Alert history and state management
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union, Set
from dataclasses import dataclass, field
from collections import defaultdict, deque
from threading import Lock
import json

import httpx

try:
    from ..config.settings import settings
    from ..utils.exceptions import ReviewBotError
    from ..utils.logger import get_logger
    from .health_checker import HealthCheckResult
    from .metrics_collector import MetricsCollector
except ImportError:
    # Fallback for standalone usage
    settings = None
    ReviewBotError = Exception
    
    def get_logger(name: str):
        import logging
        return logging.getLogger(name)
    
    class HealthCheckResult:
        def __init__(self, **kwargs):
            self.name = kwargs.get('name', 'unknown')
            self.status = kwargs.get('status', 'unknown')
            self.message = kwargs.get('message', '')
            self.timestamp = kwargs.get('timestamp', datetime.utcnow())
            self.metrics = kwargs.get('metrics', {})


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertStatus(Enum):
    """Alert status states."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


class NotificationChannel(Enum):
    """Available notification channels."""
    LOG = "log"
    WEBHOOK = "webhook"
    EMAIL = "email"
    SLACK = "slack"
    DISCORD = "discord"


@dataclass
class AlertRule:
    """Configuration for an alert rule."""
    name: str
    description: str
    severity: AlertSeverity
    enabled: bool = True
    
    # Rule conditions
    metric_name: Optional[str] = None
    threshold_value: Optional[float] = None
    comparison: str = "gt"  # gt, lt, gte, lte, eq, ne
    health_check_name: Optional[str] = None
    health_status: Optional[str] = None
    
    # Alert behavior
    consecutive_breaches: int = 1
    cooldown_minutes: int = 5
    auto_resolve_minutes: Optional[int] = None
    
    # Notification settings
    notification_channels: List[NotificationChannel] = field(default_factory=lambda: [NotificationChannel.LOG])
    webhook_url: Optional[str] = None
    notification_template: Optional[str] = None
    
    # Rate limiting
    max_notifications_per_hour: int = 10
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert rule to dictionary."""
        return {
            "name": self.name,
            "description": self.description,
            "severity": self.severity.value,
            "enabled": self.enabled,
            "metric_name": self.metric_name,
            "threshold_value": self.threshold_value,
            "comparison": self.comparison,
            "health_check_name": self.health_check_name,
            "health_status": self.health_status,
            "consecutive_breaches": self.consecutive_breaches,
            "cooldown_minutes": self.cooldown_minutes,
            "auto_resolve_minutes": self.auto_resolve_minutes,
            "notification_channels": [c.value for c in self.notification_channels],
            "webhook_url": self.webhook_url,
            "notification_template": self.notification_template,
            "max_notifications_per_hour": self.max_notifications_per_hour
        }


@dataclass
class Alert:
    """Represents an alert instance."""
    id: str
    rule_name: str
    severity: AlertSeverity
    status: AlertStatus
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    acknowledged_at: Optional[datetime] = None
    acknowledged_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "id": self.id,
            "rule_name": self.rule_name,
            "severity": self.severity.value,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "acknowledged_by": self.acknowledged_by,
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None
        }


class NotificationHandler:
    """Base class for notification handlers."""
    
    def __init__(self, channel: NotificationChannel):
        """
        Initialize notification handler.
        
        Args:
            channel: Type of notification channel
        """
        self.channel = channel
        self.logger = get_logger(f"alert_notifier.{channel.value}")
    
    async def send_notification(
        self,
        alert: Alert,
        rule: AlertRule,
        message: str
    ) -> bool:
        """
        Send notification for an alert.
        
        Args:
            alert: Alert instance
            rule: Alert rule that triggered
            message: Formatted notification message
            
        Returns:
            True if notification was sent successfully
        """
        raise NotImplementedError("Subclasses must implement send_notification")


class LogNotificationHandler(NotificationHandler):
    """Log-based notification handler."""
    
    def __init__(self):
        """Initialize log notification handler."""
        super().__init__(NotificationChannel.LOG)
    
    async def send_notification(
        self,
        alert: Alert,
        rule: AlertRule,
        message: str
    ) -> bool:
        """Send notification to logs."""
        log_level = {
            AlertSeverity.INFO: "info",
            AlertSeverity.WARNING: "warning", 
            AlertSeverity.ERROR: "error",
            AlertSeverity.CRITICAL: "critical"
        }.get(alert.severity, "warning")
        
        log_method = getattr(self.logger, log_level, self.logger.warning)
        
        log_method(
            f"ALERT: {alert.severity.value.upper()} - {alert.message}",
            extra={
                "alert_id": alert.id,
                "rule_name": alert.rule_name,
                "severity": alert.severity.value,
                "status": alert.status.value,
                "details": alert.details
            }
        )
        
        return True


class WebhookNotificationHandler(NotificationHandler):
    """Webhook notification handler."""
    
    def __init__(self):
        """Initialize webhook notification handler."""
        super().__init__(NotificationChannel.WEBHOOK)
        self.timeout = 10.0
    
    async def send_notification(
        self,
        alert: Alert,
        rule: AlertRule,
        message: str
    ) -> bool:
        """Send notification via webhook."""
        if not rule.webhook_url:
            self.logger.warning("No webhook URL configured for alert rule", extra={
                "rule_name": rule.name,
                "alert_id": alert.id
            })
            return False
        
        payload = {
            "alert_id": alert.id,
            "rule_name": alert.rule_name,
            "severity": alert.severity.value,
            "status": alert.status.value,
            "message": alert.message,
            "details": alert.details,
            "timestamp": alert.created_at.isoformat(),
            "rule": rule.to_dict()
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url=rule.webhook_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code >= 200 and response.status_code < 300:
                    self.logger.info(
                        "Webhook notification sent successfully",
                        extra={
                            "alert_id": alert.id,
                            "webhook_url": rule.webhook_url,
                            "status_code": response.status_code
                        }
                    )
                    return True
                else:
                    self.logger.error(
                        "Webhook notification failed",
                        extra={
                            "alert_id": alert.id,
                            "webhook_url": rule.webhook_url,
                            "status_code": response.status_code,
                            "response_text": response.text
                        }
                    )
                    return False
                    
        except Exception as e:
            self.logger.error(
                "Failed to send webhook notification",
                extra={
                    "alert_id": alert.id,
                    "webhook_url": rule.webhook_url,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            return False


class AlertRuleEngine:
    """Engine for evaluating alert rules against metrics and health checks."""
    
    def __init__(self):
        """Initialize alert rule engine."""
        self.logger = get_logger("alert_engine")
        self._comparison_functions = {
            "gt": lambda x, y: x > y,
            "lt": lambda x, y: x < y,
            "gte": lambda x, y: x >= y,
            "lte": lambda x, y: x <= y,
            "eq": lambda x, y: x == y,
            "ne": lambda x, y: x != y
        }
    
    def evaluate_metric_rule(
        self,
        rule: AlertRule,
        metrics: Dict[str, Any]
    ) -> bool:
        """
        Evaluate a metric-based alert rule.
        
        Args:
            rule: Alert rule to evaluate
            metrics: Current metrics data
            
        Returns:
            True if rule condition is met
        """
        if not rule.metric_name or rule.metric_name not in metrics:
            return False
        
        metric_value = metrics[rule.metric_name]
        threshold = rule.threshold_value
        
        if threshold is None:
            return False
        
        comparison_func = self._comparison_functions.get(rule.comparison)
        if not comparison_func:
            self.logger.warning(f"Unknown comparison operator: {rule.comparison}")
            return False
        
        try:
            return comparison_func(metric_value, threshold)
        except (TypeError, ValueError) as e:
            self.logger.warning(
                f"Failed to compare metric value for rule {rule.name}",
                extra={
                    "rule_name": rule.name,
                    "metric_name": rule.metric_name,
                    "metric_value": metric_value,
                    "threshold": threshold,
                    "comparison": rule.comparison,
                    "error": str(e)
                }
            )
            return False
    
    def evaluate_health_rule(
        self,
        rule: AlertRule,
        health_results: Dict[str, HealthCheckResult]
    ) -> bool:
        """
        Evaluate a health check-based alert rule.
        
        Args:
            rule: Alert rule to evaluate
            health_results: Current health check results
            
        Returns:
            True if rule condition is met
        """
        if not rule.health_check_name or not rule.health_status:
            return False
        
        health_result = health_results.get(rule.health_check_name)
        if not health_result:
            return False
        
        return health_result.status.value == rule.health_status


class AlertManager:
    """
    Main alert management system.
    
    Manages alert rules, evaluation, notifications, and lifecycle.
    """
    
    def __init__(self):
        """Initialize alert manager."""
        self.logger = get_logger("alert_manager")
        
        # Alert state
        self.rules: Dict[str, AlertRule] = {}
        self.alerts: Dict[str, Alert] = {}
        self.alert_counter = 0
        
        # State tracking for rules
        self.rule_breach_counts: Dict[str, int] = defaultdict(int)
        self.rule_last_notification: Dict[str, datetime] = {}
        self.rule_notification_counts: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        
        # Notification handlers
        self.notification_handlers: Dict[NotificationChannel, NotificationHandler] = {}
        self._setup_notification_handlers()
        
        # Rule evaluation engine
        self.rule_engine = AlertRuleEngine()
        
        # Threading safety
        self._lock = Lock()
        
        # Setup default rules
        self._setup_default_rules()
    
    def _setup_notification_handlers(self) -> None:
        """Setup notification handlers."""
        self.notification_handlers[NotificationChannel.LOG] = LogNotificationHandler()
        self.notification_handlers[NotificationChannel.WEBHOOK] = WebhookNotificationHandler()
    
    def _setup_default_rules(self) -> None:
        """Setup default alert rules based on common scenarios."""
        # High CPU usage rule
        cpu_rule = AlertRule(
            name="high_cpu_usage",
            description="High CPU usage detected",
            severity=AlertSeverity.WARNING,
            metric_name="cpu_percent",
            threshold_value=80.0,
            comparison="gt",
            consecutive_breaches=2,
            cooldown_minutes=10,
            auto_resolve_minutes=15
        )
        self.add_rule(cpu_rule)
        
        # High memory usage rule
        memory_rule = AlertRule(
            name="high_memory_usage",
            description="High memory usage detected",
            severity=AlertSeverity.WARNING,
            metric_name="memory_percent",
            threshold_value=85.0,
            comparison="gt",
            consecutive_breaches=2,
            cooldown_minutes=10,
            auto_resolve_minutes=15
        )
        self.add_rule(memory_rule)
        
        # High disk usage rule
        disk_rule = AlertRule(
            name="high_disk_usage",
            description="High disk usage detected",
            severity=AlertSeverity.ERROR,
            metric_name="disk_percent",
            threshold_value=90.0,
            comparison="gt",
            consecutive_breaches=1,
            cooldown_minutes=30,
            auto_resolve_minutes=60
        )
        self.add_rule(disk_rule)
        
        # API error rate rule
        api_error_rule = AlertRule(
            name="high_api_error_rate",
            description="High API error rate detected",
            severity=AlertSeverity.WARNING,
            metric_name="error_rate",
            threshold_value=0.1,  # 10% error rate
            comparison="gt",
            consecutive_breaches=3,
            cooldown_minutes=15
        )
        self.add_rule(api_error_rule)
        
        # Health check failure rule
        health_failure_rule = AlertRule(
            name="health_check_failure",
            description="Critical health check failure",
            severity=AlertSeverity.CRITICAL,
            health_check_name="gitlab_api",
            health_status="unhealthy",
            consecutive_breaches=2,
            cooldown_minutes=5
        )
        self.add_rule(health_failure_rule)
    
    def add_rule(self, rule: AlertRule) -> None:
        """
        Add an alert rule.
        
        Args:
            rule: Alert rule to add
        """
        with self._lock:
            self.rules[rule.name] = rule
            self.logger.info(f"Added alert rule: {rule.name}", extra={
                "rule_name": rule.name,
                "severity": rule.severity.value,
                "enabled": rule.enabled
            })
    
    def remove_rule(self, rule_name: str) -> bool:
        """
        Remove an alert rule.
        
        Args:
            rule_name: Name of rule to remove
            
        Returns:
            True if rule was removed, False if not found
        """
        with self._lock:
            if rule_name in self.rules:
                del self.rules[rule_name]
                # Clean up state tracking
                self.rule_breach_counts.pop(rule_name, None)
                self.rule_last_notification.pop(rule_name, None)
                self.rule_notification_counts.pop(rule_name, None)
                
                self.logger.info(f"Removed alert rule: {rule_name}")
                return True
            return False
    
    def get_rule(self, rule_name: str) -> Optional[AlertRule]:
        """
        Get an alert rule by name.
        
        Args:
            rule_name: Name of rule to get
            
        Returns:
            Alert rule or None if not found
        """
        return self.rules.get(rule_name)
    
    def list_rules(self) -> List[AlertRule]:
        """
        List all alert rules.
        
        Returns:
            List of all alert rules
        """
        return list(self.rules.values())
    
    def evaluate_rules(
        self,
        metrics: Optional[Dict[str, Any]] = None,
        health_results: Optional[Dict[str, HealthCheckResult]] = None
    ) -> List[Alert]:
        """
        Evaluate all enabled alert rules.
        
        Args:
            metrics: Current metrics data
            health_results: Current health check results
            
        Returns:
            List of triggered alerts
        """
        metrics = metrics or {}
        health_results = health_results or {}
        
        triggered_alerts = []
        current_time = datetime.utcnow()
        
        with self._lock:
            for rule in self.rules.values():
                if not rule.enabled:
                    continue
                
                # Evaluate rule condition
                condition_met = False
                
                if rule.metric_name:
                    condition_met = self.rule_engine.evaluate_metric_rule(rule, metrics)
                elif rule.health_check_name:
                    condition_met = self.rule_engine.evaluate_health_rule(rule, health_results)
                
                if condition_met:
                    # Track breach count
                    self.rule_breach_counts[rule.name] += 1
                    
                    # Check if we've met consecutive breach requirement
                    if (self.rule_breach_counts[rule.name] >= rule.consecutive_breaches and
                        self._should_notify(rule, current_time)):
                        
                        alert = self._create_alert(rule, metrics, health_results)
                        self.alerts[alert.id] = alert
                        triggered_alerts.append(alert)
                        
                        # Send notifications
                        asyncio.create_task(self._send_notifications(alert, rule))
                        
                        # Update notification tracking
                        self.rule_last_notification[rule.name] = current_time
                        self.rule_notification_counts[rule.name].append(current_time)
                        
                else:
                    # Reset breach count if condition is no longer met
                    self.rule_breach_counts[rule.name] = 0
        
        # Auto-resolve old alerts
        self._auto_resolve_alerts(current_time)
        
        return triggered_alerts
    
    def _should_notify(self, rule: AlertRule, current_time: datetime) -> bool:
        """
        Check if we should send notification for a rule.
        
        Args:
            rule: Alert rule to check
            current_time: Current timestamp
            
        Returns:
            True if notification should be sent
        """
        # Check cooldown
        last_notification = self.rule_last_notification.get(rule.name)
        if last_notification:
            cooldown_delta = timedelta(minutes=rule.cooldown_minutes)
            if current_time - last_notification < cooldown_delta:
                return False
        
        # Check rate limiting
        notification_times = self.rule_notification_counts[rule.name]
        one_hour_ago = current_time - timedelta(hours=1)
        recent_notifications = [t for t in notification_times if t > one_hour_ago]
        
        return len(recent_notifications) < rule.max_notifications_per_hour
    
    def _create_alert(
        self,
        rule: AlertRule,
        metrics: Dict[str, Any],
        health_results: Dict[str, HealthCheckResult]
    ) -> Alert:
        """
        Create an alert from a triggered rule.
        
        Args:
            rule: Alert rule that was triggered
            metrics: Current metrics
            health_results: Current health results
            
        Returns:
            Created alert instance
        """
        with self._lock:
            self.alert_counter += 1
            alert_id = f"alert_{self.alert_counter}_{int(time.time())}"
        
        # Create alert message
        if rule.metric_name:
            metric_value = metrics.get(rule.metric_name, "unknown")
            message = (f"{rule.description}: {rule.metric_name} = {metric_value} "
                      f"(threshold: {rule.threshold_value}, comparison: {rule.comparison})")
            details = {
                "metric_name": rule.metric_name,
                "metric_value": metric_value,
                "threshold": rule.threshold_value,
                "comparison": rule.comparison
            }
        elif rule.health_check_name:
            health_result = health_results.get(rule.health_check_name)
            status = health_result.status.value if health_result else "unknown"
            message = (f"{rule.description}: {rule.health_check_name} status = {status}")
            details = {
                "health_check_name": rule.health_check_name,
                "health_status": status,
                "health_message": health_result.message if health_result else "unknown"
            }
        else:
            message = rule.description
            details = {}
        
        return Alert(
            id=alert_id,
            rule_name=rule.name,
            severity=rule.severity,
            status=AlertStatus.ACTIVE,
            message=message,
            details=details
        )
    
    async def _send_notifications(self, alert: Alert, rule: AlertRule) -> None:
        """
        Send notifications for an alert.
        
        Args:
            alert: Alert to send notifications for
            rule: Alert rule that triggered the alert
        """
        # Format notification message
        if rule.notification_template:
            try:
                message = rule.notification_template.format(
                    alert=alert,
                    rule=rule,
                    **alert.details
                )
            except (KeyError, ValueError) as e:
                self.logger.warning(f"Failed to format notification template: {e}")
                message = alert.message
        else:
            message = alert.message
        
        # Send notifications through all configured channels
        for channel in rule.notification_channels:
            handler = self.notification_handlers.get(channel)
            if handler:
                try:
                    success = await handler.send_notification(alert, rule, message)
                    if success:
                        self.logger.info(
                            f"Notification sent via {channel.value}",
                            extra={
                                "alert_id": alert.id,
                                "channel": channel.value,
                                "rule_name": rule.name
                            }
                        )
                    else:
                        self.logger.warning(
                            f"Failed to send notification via {channel.value}",
                            extra={
                                "alert_id": alert.id,
                                "channel": channel.value,
                                "rule_name": rule.name
                            }
                        )
                except Exception as e:
                    self.logger.error(
                        f"Error sending notification via {channel.value}",
                        extra={
                            "alert_id": alert.id,
                            "channel": channel.value,
                            "rule_name": rule.name,
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        },
                        exc_info=True
                    )
    
    def _auto_resolve_alerts(self, current_time: datetime) -> None:
        """
        Auto-resolve alerts that have exceeded their auto-resolve time.
        
        Args:
            current_time: Current timestamp
        """
        alerts_to_resolve = []
        
        for alert in self.alerts.values():
            if alert.status != AlertStatus.ACTIVE:
                continue
            
            rule = self.rules.get(alert.rule_name)
            if not rule or not rule.auto_resolve_minutes:
                continue
            
            resolve_time = alert.created_at + timedelta(minutes=rule.auto_resolve_minutes)
            if current_time >= resolve_time:
                alerts_to_resolve.append(alert.id)
        
        # Resolve alerts
        for alert_id in alerts_to_resolve:
            self.resolve_alert(alert_id, "Auto-resolved after timeout")
    
    def acknowledge_alert(self, alert_id: str, acknowledged_by: str) -> bool:
        """
        Acknowledge an alert.
        
        Args:
            alert_id: ID of alert to acknowledge
            acknowledged_by: Who acknowledged the alert
            
        Returns:
            True if alert was acknowledged, False if not found
        """
        with self._lock:
            alert = self.alerts.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.ACKNOWLEDGED
            alert.acknowledged_at = datetime.utcnow()
            alert.acknowledged_by = acknowledged_by
            alert.updated_at = datetime.utcnow()
            
            self.logger.info(
                f"Alert acknowledged: {alert_id}",
                extra={
                    "alert_id": alert_id,
                    "acknowledged_by": acknowledged_by
                }
            )
            
            return True
    
    def resolve_alert(self, alert_id: str, resolved_by: str = "system") -> bool:
        """
        Resolve an alert.
        
        Args:
            alert_id: ID of alert to resolve
            resolved_by: Who resolved the alert
            
        Returns:
            True if alert was resolved, False if not found
        """
        with self._lock:
            alert = self.alerts.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.utcnow()
            alert.updated_at = datetime.utcnow()
            alert.details["resolved_by"] = resolved_by
            
            self.logger.info(
                f"Alert resolved: {alert_id}",
                extra={
                    "alert_id": alert_id,
                    "resolved_by": resolved_by
                }
            )
            
            return True
    
    def suppress_alert(self, alert_id: str, reason: str) -> bool:
        """
        Suppress an alert.
        
        Args:
            alert_id: ID of alert to suppress
            reason: Reason for suppression
            
        Returns:
            True if alert was suppressed, False if not found
        """
        with self._lock:
            alert = self.alerts.get(alert_id)
            if not alert:
                return False
            
            alert.status = AlertStatus.SUPPRESSED
            alert.updated_at = datetime.utcnow()
            alert.details["suppression_reason"] = reason
            
            self.logger.info(
                f"Alert suppressed: {alert_id}",
                extra={
                    "alert_id": alert_id,
                    "reason": reason
                }
            )
            
            return True
    
    def get_alert(self, alert_id: str) -> Optional[Alert]:
        """
        Get an alert by ID.
        
        Args:
            alert_id: ID of alert to get
            
        Returns:
            Alert instance or None if not found
        """
        return self.alerts.get(alert_id)
    
    def list_alerts(
        self,
        status: Optional[AlertStatus] = None,
        severity: Optional[AlertSeverity] = None,
        limit: Optional[int] = None
    ) -> List[Alert]:
        """
        List alerts with optional filtering.
        
        Args:
            status: Filter by alert status
            severity: Filter by alert severity
            limit: Maximum number of alerts to return
            
        Returns:
            List of alerts matching criteria
        """
        alerts = list(self.alerts.values())
        
        # Apply filters
        if status:
            alerts = [a for a in alerts if a.status == status]
        
        if severity:
            alerts = [a for a in alerts if a.severity == severity]
        
        # Sort by creation time (newest first)
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        
        # Apply limit
        if limit:
            alerts = alerts[:limit]
        
        return alerts
    
    def get_alert_statistics(self) -> Dict[str, Any]:
        """
        Get alert statistics.
        
        Returns:
            Dictionary with alert statistics
        """
        total_alerts = len(self.alerts)
        active_alerts = len([a for a in self.alerts.values() if a.status == AlertStatus.ACTIVE])
        acknowledged_alerts = len([a for a in self.alerts.values() if a.status == AlertStatus.ACKNOWLEDGED])
        resolved_alerts = len([a for a in self.alerts.values() if a.status == AlertStatus.RESOLVED])
        suppressed_alerts = len([a for a in self.alerts.values() if a.status == AlertStatus.SUPPRESSED])
        
        # Count by severity
        severity_counts = defaultdict(int)
        for alert in self.alerts.values():
            severity_counts[alert.severity.value] += 1
        
        return {
            "total_alerts": total_alerts,
            "active_alerts": active_alerts,
            "acknowledged_alerts": acknowledged_alerts,
            "resolved_alerts": resolved_alerts,
            "suppressed_alerts": suppressed_alerts,
            "severity_breakdown": dict(severity_counts),
            "total_rules": len(self.rules),
            "enabled_rules": len([r for r in self.rules.values() if r.enabled]),
            "timestamp": datetime.utcnow().isoformat()
        }
    
    def cleanup_old_alerts(self, days_to_keep: int = 30) -> int:
        """
        Clean up old resolved alerts.
        
        Args:
            days_to_keep: Number of days to keep resolved alerts
            
        Returns:
            Number of alerts cleaned up
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_to_keep)
        alerts_to_remove = []
        
        with self._lock:
            for alert_id, alert in self.alerts.items():
                if (alert.status in [AlertStatus.RESOLVED, AlertStatus.SUPPRESSED] and
                    alert.updated_at < cutoff_date):
                    alerts_to_remove.append(alert_id)
            
            for alert_id in alerts_to_remove:
                del self.alerts[alert_id]
        
        if alerts_to_remove:
            self.logger.info(
                f"Cleaned up {len(alerts_to_remove)} old alerts",
                extra={
                    "cleaned_count": len(alerts_to_remove),
                    "cutoff_days": days_to_keep
                }
            )
        
        return len(alerts_to_remove)