"""
Prometheus metrics collector for GLM Code Review Bot monitoring.

This module provides comprehensive metrics collection for:
- API response times and success rates (GitLab, GLM)
- Token usage tracking for GLM API
- System resource utilization
- Application-specific performance metrics

Features:
- Prometheus-compatible metrics with proper labeling
- Thread-safe operations for concurrent access
- Historical data tracking and aggregation
- Configurable metric collection intervals
"""

import time
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Union, Callable
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum

from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest, CONTENT_TYPE_LATEST
import psutil

try:
    from ..config.settings import settings
    from ..utils.exceptions import ReviewBotError
    from ..utils.logger import get_logger
except ImportError:
    # Fallback for standalone usage
    settings = None
    ReviewBotError = Exception
    
    def get_logger(name: str):
        import logging
        return logging.getLogger(name)


class MetricType(Enum):
    """Types of metrics supported by the collector."""
    COUNTER = "counter"
    HISTOGRAM = "histogram"
    GAUGE = "gauge"
    SUMMARY = "summary"


@dataclass
class MetricConfig:
    """Configuration for a metric."""
    name: str
    description: str
    metric_type: MetricType
    label_names: List[str] = field(default_factory=list)
    buckets: Optional[List[float]] = None  # For histograms


class APITracker:
    """
    Tracker for API metrics including response times, success rates, and usage statistics.
    
    Thread-safe implementation for concurrent tracking across multiple API clients.
    """
    
    def __init__(self, api_name: str):
        """
        Initialize API tracker.
        
        Args:
            api_name: Name of the API being tracked (e.g., 'gitlab', 'glm')
        """
        self.api_name = api_name
        self.logger = get_logger(f"metrics.{api_name}")
        self._lock = threading.RLock()
        
        # Metrics storage
        self.request_count = 0
        self.success_count = 0
        self.error_count = 0
        self.total_response_time = 0.0
        self.min_response_time = float('inf')
        self.max_response_time = 0.0
        self.response_times = deque(maxlen=1000)  # Keep last 1000 response times
        self.status_codes = defaultdict(int)
        self.errors = defaultdict(int)
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
    
    def _setup_prometheus_metrics(self) -> None:
        """Setup Prometheus metrics for this API."""
        # Create a registry for this API
        self.registry = CollectorRegistry()
        
        # Request counter with labels for status and method
        self.request_counter = Counter(
            f'{self.api_name}_api_requests_total',
            f'Total number of {self.api_name} API requests',
            ['method', 'status_code', 'success'],
            registry=self.registry
        )
        
        # Response time histogram
        self.response_time_histogram = Histogram(
            f'{self.api_name}_api_response_time_seconds',
            f'Response time for {self.api_name} API requests',
            ['method', 'status_code'],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf')],
            registry=self.registry
        )
        
        # Error counter
        self.error_counter = Counter(
            f'{self.api_name}_api_errors_total',
            f'Total number of {self.api_name} API errors',
            ['method', 'error_type', 'status_code'],
            registry=self.registry
        )
        
        # Success rate gauge
        self.success_rate_gauge = Gauge(
            f'{self.api_name}_api_success_rate',
            f'Success rate for {self.api_name} API requests',
            registry=self.registry
        )
    
    def record_request(
        self,
        method: str,
        status_code: int,
        response_time_ms: float,
        error: Optional[Exception] = None
    ) -> None:
        """
        Record an API request with metrics.
        
        Args:
            method: HTTP method used
            status_code: HTTP status code received
            response_time_ms: Response time in milliseconds
            error: Exception if request failed
        """
        response_time_sec = response_time_ms / 1000.0
        success = error is None and 200 <= status_code < 400
        
        with self._lock:
            self.request_count += 1
            self.total_response_time += response_time_sec
            self.response_times.append(response_time_sec)
            self.status_codes[str(status_code)] += 1
            
            if success:
                self.success_count += 1
            else:
                self.error_count += 1
                if error:
                    self.errors[type(error).__name__] += 1
            
            # Update min/max
            self.min_response_time = min(self.min_response_time, response_time_sec)
            self.max_response_time = max(self.max_response_time, response_time_sec)
        
        # Update Prometheus metrics
        self.request_counter.labels(
            method=method,
            status_code=str(status_code),
            success=str(success).lower()
        ).inc()
        
        self.response_time_histogram.labels(
            method=method,
            status_code=str(status_code)
        ).observe(response_time_sec)
        
        if not success:
            error_type = type(error).__name__ if error else 'http_error'
            self.error_counter.labels(
                method=method,
                error_type=error_type,
                status_code=str(status_code)
            ).inc()
        
        # Update success rate gauge
        self._update_success_rate()
        
        # Log detailed metrics
        if error:
            self.logger.warning(
                f"API request failed: {self.api_name} {method}",
                extra={
                    "api_name": self.api_name,
                    "method": method,
                    "status_code": status_code,
                    "response_time_ms": response_time_ms,
                    "error_type": type(error).__name__,
                    "error_message": str(error)
                }
            )
        else:
            self.logger.debug(
                f"API request recorded: {self.api_name} {method}",
                extra={
                    "api_name": self.api_name,
                    "method": method,
                    "status_code": status_code,
                    "response_time_ms": response_time_ms
                }
            )
    
    def _update_success_rate(self) -> None:
        """Update success rate gauge based on current statistics."""
        with self._lock:
            if self.request_count > 0:
                success_rate = self.success_count / self.request_count
                self.success_rate_gauge.set(success_rate)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get current API statistics.
        
        Returns:
            Dictionary with comprehensive API metrics
        """
        with self._lock:
            avg_response_time = (self.total_response_time / self.request_count 
                               if self.request_count > 0 else 0.0)
            
            # Calculate percentiles from recent response times
            percentiles = {}
            if self.response_times:
                sorted_times = sorted(self.response_times)
                length = len(sorted_times)
                
                percentiles = {
                    'p50': sorted_times[int(length * 0.5)],
                    'p95': sorted_times[int(length * 0.95)],
                    'p99': sorted_times[int(length * 0.99)]
                }
            
            return {
                'api_name': self.api_name,
                'request_count': self.request_count,
                'success_count': self.success_count,
                'error_count': self.error_count,
                'success_rate': (self.success_count / self.request_count 
                                if self.request_count > 0 else 0.0),
                'avg_response_time_sec': avg_response_time,
                'min_response_time_sec': self.min_response_time if self.min_response_time != float('inf') else 0.0,
                'max_response_time_sec': self.max_response_time,
                'response_times': list(self.response_times)[-100:],  # Last 100
                'status_codes': dict(self.status_codes),
                'errors': dict(self.errors),
                'percentiles': percentiles
            }
    
    def reset_metrics(self) -> None:
        """Reset all metrics to initial state."""
        with self._lock:
            self.request_count = 0
            self.success_count = 0
            self.error_count = 0
            self.total_response_time = 0.0
            self.min_response_time = float('inf')
            self.max_response_time = 0.0
            self.response_times.clear()
            self.status_codes.clear()
            self.errors.clear()
        
        # Reset Prometheus metrics
        self.request_counter.clear()
        self.response_time_histogram.clear()
        self.error_counter.clear()
        self.success_rate_gauge.set(0.0)
        
        self.logger.info(f"Reset metrics for API: {self.api_name}")


class TokenUsageTracker:
    """
    Tracker for GLM API token usage.
    
    Monitors token consumption for cost management and rate limiting.
    """
    
    def __init__(self):
        """Initialize token usage tracker."""
        self.logger = get_logger("metrics.token_usage")
        self._lock = threading.RLock()
        
        # Token usage metrics
        self.total_tokens_used = 0
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.request_count = 0
        self.usage_by_date = defaultdict(int)
        self.usage_by_model = defaultdict(int)
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        
        self.token_counter = Counter(
            'glm_tokens_total',
            'Total GLM API tokens used',
            ['model', 'type'],  # type can be 'prompt', 'completion', 'total'
            registry=self.registry
        )
        
        self.token_usage_gauge = Gauge(
            'glm_token_usage_daily',
            'Daily GLM token usage',
            registry=self.registry
        )
        
        self.request_counter = Counter(
            'glm_requests_total',
            'Total GLM API requests',
            ['model', 'success'],
            registry=self.registry
        )
    
    def record_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "glm-4",
        success: bool = True
    ) -> None:
        """
        Record token usage for a GLM API request.
        
        Args:
            prompt_tokens: Number of tokens in the prompt
            completion_tokens: Number of tokens in the completion
            model: GLM model used
            success: Whether the request was successful
        """
        total_tokens = prompt_tokens + completion_tokens
        today = datetime.utcnow().strftime('%Y-%m-%d')
        
        with self._lock:
            self.total_tokens_used += total_tokens
            self.prompt_tokens += prompt_tokens
            self.completion_tokens += completion_tokens
            self.request_count += 1
            self.usage_by_date[today] += total_tokens
            self.usage_by_model[model] += total_tokens
        
        # Update Prometheus metrics
        self.token_counter.labels(model=model, type='prompt').inc(prompt_tokens)
        self.token_counter.labels(model=model, type='completion').inc(completion_tokens)
        self.token_counter.labels(model=model, type='total').inc(total_tokens)
        
        self.token_usage_gauge.set(self.usage_by_date[today])
        
        self.request_counter.labels(model=model, success=str(success).lower()).inc()
        
        self.logger.debug(
            "Token usage recorded",
            extra={
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": total_tokens,
                "model": model,
                "success": success,
                "daily_usage": self.usage_by_date[today]
            }
        )
    
    def get_usage_statistics(self) -> Dict[str, Any]:
        """
        Get current token usage statistics.
        
        Returns:
            Dictionary with token usage metrics
        """
        with self._lock:
            return {
                'total_tokens_used': self.total_tokens_used,
                'prompt_tokens': self.prompt_tokens,
                'completion_tokens': self.completion_tokens,
                'request_count': self.request_count,
                'avg_tokens_per_request': (self.total_tokens_used / self.request_count 
                                         if self.request_count > 0 else 0.0),
                'usage_by_date': dict(self.usage_by_date),
                'usage_by_model': dict(self.usage_by_model),
                'today_usage': self.usage_by_date[datetime.utcnow().strftime('%Y-%m-%d')]
            }
    
    def reset_metrics(self) -> None:
        """Reset all token usage metrics."""
        with self._lock:
            self.total_tokens_used = 0
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.request_count = 0
            self.usage_by_date.clear()
            self.usage_by_model.clear()
        
        # Reset Prometheus metrics
        self.token_counter.clear()
        self.token_usage_gauge.set(0.0)
        self.request_counter.clear()
        
        self.logger.info("Reset token usage metrics")


class SystemMetricsCollector:
    """
    Collector for system resource metrics.
    
    Monitors CPU, memory, disk, and network usage with historical tracking.
    """
    
    def __init__(self, collection_interval: int = 60):
        """
        Initialize system metrics collector.
        
        Args:
            collection_interval: Interval in seconds for metric collection
        """
        self.collection_interval = collection_interval
        self.logger = get_logger("metrics.system")
        self._lock = threading.RLock()
        self._running = False
        self._thread = None
        
        # Historical data
        self.cpu_history = deque(maxlen=1000)
        self.memory_history = deque(maxlen=1000)
        self.disk_history = deque(maxlen=1000)
        
        # Prometheus metrics
        self.registry = CollectorRegistry()
        
        self.cpu_gauge = Gauge(
            'system_cpu_usage_percent',
            'System CPU usage percentage',
            registry=self.registry
        )
        
        self.memory_gauge = Gauge(
            'system_memory_usage_percent',
            'System memory usage percentage',
            registry=self.registry
        )
        
        self.disk_gauge = Gauge(
            'system_disk_usage_percent',
            'System disk usage percentage',
            registry=self.registry
        )
        
        self.memory_available_gb = Gauge(
            'system_memory_available_gb',
            'Available system memory in GB',
            registry=self.registry
        )
        
        self.disk_free_gb = Gauge(
            'system_disk_free_gb',
            'Available disk space in GB',
            registry=self.registry
        )
    
    def start_collection(self) -> None:
        """Start background metric collection."""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._collect_loop, daemon=True)
        self._thread.start()
        self.logger.info("Started system metrics collection")
    
    def stop_collection(self) -> None:
        """Stop background metric collection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        self.logger.info("Stopped system metrics collection")
    
    def _collect_loop(self) -> None:
        """Background thread loop for collecting metrics."""
        while self._running:
            try:
                self._collect_metrics()
                time.sleep(self.collection_interval)
            except Exception as e:
                self.logger.error(
                    "Error collecting system metrics",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                time.sleep(self.collection_interval)
    
    def _collect_metrics(self) -> None:
        """Collect current system metrics."""
        timestamp = datetime.utcnow()
        
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        memory_available_gb = memory.available / (1024**3)
        
        # Disk usage
        disk = psutil.disk_usage('.')
        disk_percent = (disk.used / disk.total) * 100
        disk_free_gb = disk.free / (1024**3)
        
        with self._lock:
            self.cpu_history.append((timestamp, cpu_percent))
            self.memory_history.append((timestamp, memory_percent))
            self.disk_history.append((timestamp, disk_percent))
        
        # Update Prometheus metrics
        self.cpu_gauge.set(cpu_percent)
        self.memory_gauge.set(memory_percent)
        self.disk_gauge.set(disk_percent)
        self.memory_available_gb.set(memory_available_gb)
        self.disk_free_gb.set(disk_free_gb)
        
        self.logger.debug(
            "System metrics collected",
            extra={
                "cpu_percent": cpu_percent,
                "memory_percent": memory_percent,
                "disk_percent": disk_percent,
                "memory_available_gb": memory_available_gb,
                "disk_free_gb": disk_free_gb
            }
        )
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """
        Get current system metrics.
        
        Returns:
            Dictionary with current system metrics
        """
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('.')
            
            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_percent': (disk.used / disk.total) * 100,
                'memory_available_gb': memory.available / (1024**3),
                'disk_free_gb': disk.free / (1024**3),
                'timestamp': datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error getting current metrics: {e}")
            return {}
    
    def get_historical_metrics(
        self,
        hours: int = 1,
        metric_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Get historical system metrics.
        
        Args:
            hours: Number of hours of history to return
            metric_type: Type of metrics to return ('cpu', 'memory', 'disk', 'all')
            
        Returns:
            Dictionary with historical metrics
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        with self._lock:
            result = {}
            
            if metric_type in ['cpu', 'all']:
                cpu_data = [(t.isoformat(), v) for t, v in self.cpu_history if t >= cutoff_time]
                result['cpu'] = cpu_data
            
            if metric_type in ['memory', 'all']:
                memory_data = [(t.isoformat(), v) for t, v in self.memory_history if t >= cutoff_time]
                result['memory'] = memory_data
            
            if metric_type in ['disk', 'all']:
                disk_data = [(t.isoformat(), v) for t, v in self.disk_history if t >= cutoff_time]
                result['disk'] = disk_data
        
        return result


class MetricsCollector:
    """
    Main metrics collector orchestrator.
    
    Manages all metrics collectors and provides unified access to metrics data.
    """
    
    def __init__(self, collection_interval: int = 60):
        """
        Initialize metrics collector.
        
        Args:
            collection_interval: Interval for system metrics collection
        """
        self.logger = get_logger("metrics_collector")
        self.collection_interval = collection_interval
        
        # Initialize collectors
        self.api_trackers: Dict[str, APITracker] = {}
        self.token_tracker = TokenUsageTracker()
        self.system_collector = SystemMetricsCollector(collection_interval)
        
        # Main Prometheus registry
        self.registry = CollectorRegistry()
        
        # Add some general metrics
        self.app_uptime = Gauge(
            'app_uptime_seconds',
            'Application uptime in seconds',
            registry=self.registry
        )
        
        self.start_time = time.time()
        
        # Setup default API trackers
        self._setup_default_trackers()
    
    def _setup_default_trackers(self) -> None:
        """Setup default API trackers based on configuration."""
        # GitLab API tracker
        if settings and settings.gitlab_token:
            self.setup_api_tracker("gitlab")
        
        # GLM API tracker
        if settings and settings.glm_api_key:
            self.setup_api_tracker("glm")
    
    def setup_api_tracker(self, api_name: str) -> APITracker:
        """
        Setup an API tracker for a specific API.
        
        Args:
            api_name: Name of the API to track
            
        Returns:
            The created or existing API tracker
        """
        if api_name not in self.api_trackers:
            tracker = APITracker(api_name)
            self.api_trackers[api_name] = tracker
            self.logger.info(f"Setup API tracker: {api_name}")
        
        return self.api_trackers[api_name]
    
    def record_api_request(
        self,
        api_name: str,
        method: str,
        status_code: int,
        response_time_ms: float,
        error: Optional[Exception] = None
    ) -> None:
        """
        Record an API request metrics.
        
        Args:
            api_name: Name of the API (gitlab, glm)
            method: HTTP method
            status_code: HTTP status code
            response_time_ms: Response time in milliseconds
            error: Exception if request failed
        """
        tracker = self.api_trackers.get(api_name)
        if tracker:
            tracker.record_request(method, status_code, response_time_ms, error)
        else:
            self.logger.warning(f"No tracker found for API: {api_name}")
    
    def record_token_usage(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: str = "glm-4",
        success: bool = True
    ) -> None:
        """
        Record GLM API token usage.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            model: GLM model used
            success: Whether request was successful
        """
        self.token_tracker.record_usage(prompt_tokens, completion_tokens, model, success)
    
    def start_collection(self) -> None:
        """Start all metric collection processes."""
        self.system_collector.start_collection()
        self.logger.info("Started metrics collection")
    
    def stop_collection(self) -> None:
        """Stop all metric collection processes."""
        self.system_collector.stop_collection()
        self.logger.info("Stopped metrics collection")
    
    def get_all_metrics(self) -> Dict[str, Any]:
        """
        Get all collected metrics.
        
        Returns:
            Dictionary with comprehensive metrics data
        """
        # Update uptime gauge
        self.app_uptime.set(time.time() - self.start_time)
        
        metrics = {
            'uptime_seconds': time.time() - self.start_time,
            'api_metrics': {name: tracker.get_statistics() 
                          for name, tracker in self.api_trackers.items()},
            'token_usage': self.token_tracker.get_usage_statistics(),
            'system_metrics': self.system_collector.get_current_metrics(),
            'timestamp': datetime.utcnow().isoformat()
        }
        
        return metrics
    
    def get_prometheus_metrics(self, registry_name: str = "main") -> str:
        """
        Get Prometheus metrics in the standard format.
        
        Args:
            registry_name: Name of the registry to export from
            
        Returns:
            Prometheus metrics as string
        """
        if registry_name == "main":
            # Update uptime before export
            self.app_uptime.set(time.time() - self.start_time)
            return generate_latest(self.registry).decode('utf-8')
        elif registry_name in self.api_trackers:
            return generate_latest(self.api_trackers[registry_name].registry).decode('utf-8')
        elif registry_name == "tokens":
            return generate_latest(self.token_tracker.registry).decode('utf-8')
        elif registry_name == "system":
            return generate_latest(self.system_collector.registry).decode('utf-8')
        else:
            return ""
    
    def reset_metrics(self, api_name: Optional[str] = None) -> None:
        """
        Reset metrics.
        
        Args:
            api_name: Specific API to reset, or None for all
        """
        if api_name and api_name in self.api_trackers:
            self.api_trackers[api_name].reset_metrics()
            self.logger.info(f"Reset metrics for API: {api_name}")
        else:
            for tracker in self.api_trackers.values():
                tracker.reset_metrics()
            self.token_tracker.reset_metrics()
            self.logger.info("Reset all metrics")
    
    def get_api_tracker(self, api_name: str) -> Optional[APITracker]:
        """
        Get API tracker by name.
        
        Args:
            api_name: Name of the API tracker
            
        Returns:
            API tracker instance or None
        """
        return self.api_trackers.get(api_name)
    
    def list_available_registries(self) -> List[str]:
        """
        List all available Prometheus registries.
        
        Returns:
            List of registry names
        """
        registries = ["main", "tokens", "system"]
        registries.extend(self.api_trackers.keys())
        return registries