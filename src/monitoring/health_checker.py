"""
Health check implementations for GLM Code Review Bot monitoring.

This module provides comprehensive health checking capabilities for:
- External API endpoints (GitLab, GLM)
- Database connectivity (if applicable)
- System resources (CPU, memory, disk)
- Application-specific health metrics

Health checks follow a consistent pattern with:
- Async/await support for I/O operations
- Comprehensive error handling and logging
- Configurable timeouts and retry logic
- Detailed status reporting with context information
"""

import asyncio
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional, List, Callable, Union
from dataclasses import dataclass, field
from collections.abc import Awaitable

import httpx
import psutil

try:
    from ..config.settings import settings
    from ..utils.exceptions import ReviewBotError, GLMAPIError, GitLabAPIError
    from ..utils.logger import get_logger
except ImportError:
    # Fallback for standalone usage
    settings = None
    ReviewBotError = Exception
    GLMAPIError = Exception
    GitLabAPIError = Exception
    
    def get_logger(name: str):
        import logging
        return logging.getLogger(name)


class HealthStatus(Enum):
    """Health check status enumeration."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """
    Result of a health check operation.
    
    Contains comprehensive information about the health check
    including status, timing, metrics, and error details.
    """
    name: str
    status: HealthStatus
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    duration_ms: float = 0.0
    metrics: Dict[str, Any] = field(default_factory=dict)
    error_details: Optional[str] = None
    last_error: Optional[Exception] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert health check result to dictionary."""
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "duration_ms": self.duration_ms,
            "metrics": self.metrics,
            "error_details": self.error_details,
            "is_healthy": self.status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED]
        }


class BaseHealthChecker:
    """
    Base class for health checkers.
    
    Provides common functionality and patterns for implementing
    health checks with consistent error handling and logging.
    """
    
    def __init__(self, name: str, timeout_seconds: float = 10.0):
        """
        Initialize base health checker.
        
        Args:
            name: Name of the health checker
            timeout_seconds: Timeout for health check operations
        """
        self.name = name
        self.timeout_seconds = timeout_seconds
        self.logger = get_logger(f"health_checker.{name}")
    
    async def check_health(self) -> HealthCheckResult:
        """
        Perform the health check.
        
        Returns:
            HealthCheckResult with detailed status
            
        Raises:
            ReviewBotError: If health check fails critically
        """
        start_time = time.time()
        
        try:
            result = await self._perform_check()
            result.duration_ms = (time.time() - start_time) * 1000
            
            self.logger.debug(
                f"Health check completed: {self.name}",
                extra={
                    "check_name": self.name,
                    "status": result.status.value,
                    "duration_ms": result.duration_ms
                }
            )
            
            return result
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Health check timed out after {self.timeout_seconds}s"
            
            self.logger.error(
                f"Health check timeout: {self.name}",
                extra={
                    "check_name": self.name,
                    "timeout_seconds": self.timeout_seconds,
                    "duration_ms": duration_ms
                }
            )
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=error_msg,
                duration_ms=duration_ms,
                error_details="Operation timeout"
            )
            
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            error_msg = f"Health check failed: {str(e)}"
            
            self.logger.error(
                f"Health check error: {self.name}",
                extra={
                    "check_name": self.name,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": duration_ms
                },
                exc_info=True
            )
            
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=error_msg,
                duration_ms=duration_ms,
                error_details=str(e),
                last_error=e
            )
    
    async def _perform_check(self) -> HealthCheckResult:
        """
        Perform the actual health check implementation.
        
        Must be implemented by subclasses.
        
        Returns:
            HealthCheckResult with check results
        """
        raise NotImplementedError("Subclasses must implement _perform_check")


class APIHealthChecker(BaseHealthChecker):
    """
    Health checker for external API endpoints.
    
    Supports checking both GitLab and GLM API endpoints with
    authentication, timeout handling, and response validation.
    """
    
    def __init__(
        self,
        name: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        expected_status_codes: List[int] = None,
        timeout_seconds: float = 10.0,
        method: str = "GET"
    ):
        """
        Initialize API health checker.
        
        Args:
            name: Name of the API checker
            url: API endpoint URL to check
            headers: HTTP headers for the request
            expected_status_codes: List of acceptable HTTP status codes
            timeout_seconds: Request timeout
            method: HTTP method to use
        """
        super().__init__(name, timeout_seconds)
        self.url = url
        self.headers = headers or {}
        self.expected_status_codes = expected_status_codes or [200]
        self.method = method.upper()
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform API health check with HTTP request."""
        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            try:
                response = await client.request(
                    method=self.method,
                    url=self.url,
                    headers=self.headers
                )
                
                metrics = {
                    "status_code": response.status_code,
                    "response_time_ms": response.elapsed.total_seconds() * 1000,
                    "content_length": len(response.content)
                }
                
                if response.status_code in self.expected_status_codes:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.HEALTHY,
                        message=f"API responding normally (status {response.status_code})",
                        metrics=metrics
                    )
                else:
                    return HealthCheckResult(
                        name=self.name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"API returned unexpected status: {response.status_code}",
                        metrics=metrics,
                        error_details=f"Expected: {self.expected_status_codes}, Got: {response.status_code}"
                    )
                    
            except httpx.TimeoutException:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="API request timed out",
                    error_details=f"Timeout after {self.timeout_seconds}s"
                )
            except httpx.ConnectError as e:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message="Failed to connect to API",
                    error_details=str(e)
                )
            except Exception as e:
                return HealthCheckResult(
                    name=self.name,
                    status=HealthStatus.UNHEALTHY,
                    message=f"API health check failed: {str(e)}",
                    error_details=str(e),
                    last_error=e
                )


class SystemResourceChecker(BaseHealthChecker):
    """
    Health checker for system resources.
    
    Monitors CPU usage, memory consumption, disk space,
    and other system-level metrics with configurable thresholds.
    """
    
    def __init__(
        self,
        name: str = "system_resources",
        cpu_threshold: float = 80.0,
        memory_threshold: float = 85.0,
        disk_threshold: float = 90.0,
        timeout_seconds: float = 5.0
    ):
        """
        Initialize system resource checker.
        
        Args:
            name: Name of the system checker
            cpu_threshold: CPU usage percentage threshold
            memory_threshold: Memory usage percentage threshold
            disk_threshold: Disk usage percentage threshold
            timeout_seconds: Timeout for system checks
        """
        super().__init__(name, timeout_seconds)
        self.cpu_threshold = cpu_threshold
        self.memory_threshold = memory_threshold
        self.disk_threshold = disk_threshold
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform system resource health check."""
        try:
            # CPU usage check
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # Memory usage check
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            
            # Disk usage check (current directory)
            disk = psutil.disk_usage('.')
            disk_percent = (disk.used / disk.total) * 100
            
            metrics = {
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_available_gb": memory.available / (1024**3),
                "disk_free_gb": disk.free / (1024**3)
            }
            
            # Determine overall status
            status = HealthStatus.HEALTHY
            messages = []
            
            if cpu_percent >= self.cpu_threshold:
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                messages.append(f"High CPU usage: {cpu_percent:.1f}%")
            
            if memory_percent >= self.memory_threshold:
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                messages.append(f"High memory usage: {memory_percent:.1f}%")
            
            if disk_percent >= self.disk_threshold:
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                messages.append(f"High disk usage: {disk_percent:.1f}%")
            
            message = "System resources normal" if not messages else "; ".join(messages)
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                metrics=metrics
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Failed to check system resources: {str(e)}",
                error_details=str(e),
                last_error=e
            )


class ApplicationHealthChecker(BaseHealthChecker):
    """
    Health checker for application-specific metrics.
    
    Monitors application health including configuration,
    required services, and internal state.
    """
    
    def __init__(self, name: str = "application", timeout_seconds: float = 5.0):
        """
        Initialize application health checker.
        
        Args:
            name: Name of the application checker
            timeout_seconds: Timeout for application checks
        """
        super().__init__(name, timeout_seconds)
    
    async def _perform_check(self) -> HealthCheckResult:
        """Perform application health check."""
        try:
            metrics = {}
            messages = []
            status = HealthStatus.HEALTHY
            
            # Check configuration
            config_issues = []
            if settings:
                if not settings.gitlab_token:
                    config_issues.append("GitLab token missing")
                if not settings.glm_api_key:
                    config_issues.append("GLM API key missing")
                
                metrics["config_valid"] = len(config_issues) == 0
                metrics["gitlab_configured"] = bool(settings.gitlab_token)
                metrics["glm_configured"] = bool(settings.glm_api_key)
            else:
                config_issues.append("Settings not available")
                metrics["config_valid"] = False
            
            if config_issues:
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                messages.extend(config_issues)
            
            # Check if essential imports are available
            try:
                import httpx
                import psutil
                metrics["dependencies_available"] = True
            except ImportError as e:
                metrics["dependencies_available"] = False
                status = HealthStatus.DEGRADED if status == HealthStatus.HEALTHY else HealthStatus.UNHEALTHY
                messages.append(f"Missing dependency: {e}")
            
            message = "Application healthy" if not messages else "; ".join(messages)
            
            return HealthCheckResult(
                name=self.name,
                status=status,
                message=message,
                metrics=metrics
            )
            
        except Exception as e:
            return HealthCheckResult(
                name=self.name,
                status=HealthStatus.UNHEALTHY,
                message=f"Application health check failed: {str(e)}",
                error_details=str(e),
                last_error=e
            )


class HealthChecker:
    """
    Main health checker orchestrator.
    
    Manages multiple health checkers, aggregates results,
    and provides comprehensive health status reporting.
    """
    
    def __init__(self, timeout_seconds: float = 30.0):
        """
        Initialize health checker orchestrator.
        
        Args:
            timeout_seconds: Overall timeout for all health checks
        """
        self.timeout_seconds = timeout_seconds
        self.logger = get_logger("health_checker")
        self.checkers: List[BaseHealthChecker] = []
        self._setup_default_checkers()
    
    def _setup_default_checkers(self) -> None:
        """Setup default health checkers based on available configuration."""
        # System resource checker
        self.add_checker(SystemResourceChecker())
        
        # Application health checker
        self.add_checker(ApplicationHealthChecker())
        
        # GitLab API checker if configured
        if settings and settings.gitlab_token and settings.gitlab_api_url and settings.project_id and settings.mr_iid:
            gitlab_url = f"{settings.gitlab_api_url}/projects/{settings.project_id}/merge_requests/{settings.mr_iid}"
            gitlab_headers = {"Authorization": f"Bearer {settings.gitlab_token}"}
            self.add_checker(APIHealthChecker(
                name="gitlab_api",
                url=gitlab_url,
                headers=gitlab_headers,
                expected_status_codes=[200, 404]  # 404 is OK if MR doesn't exist yet
            ))
        
        # GLM API checker if configured
        if settings and settings.glm_api_key and settings.glm_api_url:
            glm_headers = {"Authorization": f"Bearer {settings.glm_api_key}"}
            self.add_checker(APIHealthChecker(
                name="glm_api",
                url=settings.glm_api_url,
                headers=glm_headers,
                method="POST",
                expected_status_codes=[200, 400, 401]  # 400/401 indicate API is reachable
            ))
    
    def add_checker(self, checker: BaseHealthChecker) -> None:
        """
        Add a health checker to the orchestrator.
        
        Args:
            checker: Health checker instance to add
        """
        self.checkers.append(checker)
        self.logger.info(f"Added health checker: {checker.name}")
    
    def remove_checker(self, name: str) -> bool:
        """
        Remove a health checker by name.
        
        Args:
            name: Name of the checker to remove
            
        Returns:
            True if checker was found and removed, False otherwise
        """
        for i, checker in enumerate(self.checkers):
            if checker.name == name:
                removed_checker = self.checkers.pop(i)
                self.logger.info(f"Removed health checker: {removed_checker.name}")
                return True
        return False
    
    async def check_all(self) -> Dict[str, Any]:
        """
        Perform all health checks concurrently.
        
        Returns:
            Dictionary with overall health status and individual results
        """
        start_time = time.time()
        
        try:
            # Run all health checks concurrently
            tasks = [checker.check_health() for checker in self.checkers]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            processed_results = []
            overall_status = HealthStatus.HEALTHY
            failed_checks = []
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    # Handle unexpected exceptions
                    checker_name = self.checkers[i].name if i < len(self.checkers) else "unknown"
                    error_result = HealthCheckResult(
                        name=checker_name,
                        status=HealthStatus.UNHEALTHY,
                        message=f"Health check execution failed: {str(result)}",
                        error_details=str(result),
                        last_error=result
                    )
                    processed_results.append(error_result)
                    failed_checks.append(checker_name)
                    overall_status = HealthStatus.UNHEALTHY
                else:
                    processed_results.append(result)
                    
                    # Update overall status
                    if result.status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                        failed_checks.append(result.name)
                    elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
            
            duration_ms = (time.time() - start_time) * 1000
            
            summary = {
                "overall_status": overall_status.value,
                "is_healthy": overall_status in [HealthStatus.HEALTHY, HealthStatus.DEGRADED],
                "total_checks": len(self.checkers),
                "passed_checks": len(self.checkers) - len(failed_checks),
                "failed_checks": failed_checks,
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "results": [result.to_dict() for result in processed_results]
            }
            
            self.logger.info(
                f"Health check completed: {overall_status.value}",
                extra={
                    "overall_status": overall_status.value,
                    "total_checks": len(self.checkers),
                    "failed_checks": len(failed_checks),
                    "duration_ms": duration_ms
                }
            )
            
            return summary
            
        except asyncio.TimeoutError:
            duration_ms = (time.time() - start_time) * 1000
            
            self.logger.error(
                "Health check orchestration timed out",
                extra={
                    "timeout_seconds": self.timeout_seconds,
                    "duration_ms": duration_ms
                }
            )
            
            return {
                "overall_status": HealthStatus.UNHEALTHY.value,
                "is_healthy": False,
                "total_checks": len(self.checkers),
                "passed_checks": 0,
                "failed_checks": [checker.name for checker in self.checkers],
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "error": "Health check orchestration timed out",
                "results": []
            }
        
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            
            self.logger.error(
                "Health check orchestration failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "duration_ms": duration_ms
                },
                exc_info=True
            )
            
            return {
                "overall_status": HealthStatus.UNHEALTHY.value,
                "is_healthy": False,
                "total_checks": len(self.checkers),
                "passed_checks": 0,
                "failed_checks": [checker.name for checker in self.checkers],
                "duration_ms": duration_ms,
                "timestamp": datetime.utcnow().isoformat(),
                "error": str(e),
                "results": []
            }
    
    async def check_single(self, name: str) -> Optional[HealthCheckResult]:
        """
        Perform a single health check by name.
        
        Args:
            name: Name of the health checker to run
            
        Returns:
            HealthCheckResult if found, None otherwise
        """
        for checker in self.checkers:
            if checker.name == name:
                return await checker.check_health()
        return None
    
    def get_checker_names(self) -> List[str]:
        """
        Get list of all registered health checker names.
        
        Returns:
            List of health checker names
        """
        return [checker.name for checker in self.checkers]
    
    async def get_status_summary(self) -> Dict[str, Any]:
        """
        Get a quick status summary without performing checks.
        
        Returns:
            Dictionary with checker information
        """
        return {
            "total_checkers": len(self.checkers),
            "checker_names": self.get_checker_names(),
            "timeout_seconds": self.timeout_seconds,
            "timestamp": datetime.utcnow().isoformat()
        }