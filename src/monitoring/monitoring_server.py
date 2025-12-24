"""
FastAPI monitoring server for GLM Code Review Bot.

This module provides a FastAPI-based HTTP server for exposing:
- Health check endpoints
- Prometheus metrics endpoints
- Application status and configuration information
- Administrative interfaces for monitoring

Features:
- Clean async/await architecture
- Comprehensive endpoint documentation
- Integration with health checks and metrics collectors
- Configurable server settings and security
"""

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
import uvicorn

try:
    from ..config.settings import settings
    from ..utils.exceptions import ReviewBotError
    from ..utils.logger import get_logger
    from .health_checker import HealthChecker
    from .metrics_collector import MetricsCollector
except ImportError:
    # Fallback for standalone usage
    settings = None
    ReviewBotError = Exception
    
    def get_logger(name: str):
        import logging
        return logging.getLogger(name)
    
    class HealthChecker:
        def __init__(self, *args, **kwargs):
            pass
        
        async def check_all(self):
            return {"overall_status": "unknown", "results": []}
        
        def get_checker_names(self):
            return []
        
        async def get_status_summary(self):
            return {"total_checkers": 0, "checker_names": []}
    
    class MetricsCollector:
        def __init__(self, *args, **kwargs):
            pass
        
        def get_all_metrics(self):
            return {}
        
        def get_prometheus_metrics(self, registry_name: str = "main") -> str:
            return ""
        
        def list_available_registries(self):
            return ["main"]
        
        def start_collection(self):
            pass
        
        def stop_collection(self):
            pass


@dataclass
class ServerConfig:
    """Configuration for the monitoring server."""
    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "info"
    enable_cors: bool = True
    cors_origins: List[str] = None
    workers: int = 1
    reload: bool = False


class MonitoringServer:
    """
    FastAPI-based monitoring server.
    
    Provides HTTP endpoints for health checks, metrics, and
    administrative functions with comprehensive error handling.
    """
    
    def __init__(
        self,
        health_checker: Optional[HealthChecker] = None,
        metrics_collector: Optional[MetricsCollector] = None,
        config: Optional[ServerConfig] = None
    ):
        """
        Initialize monitoring server.
        
        Args:
            health_checker: Health checker instance
            metrics_collector: Metrics collector instance
            config: Server configuration
        """
        self.logger = get_logger("monitoring_server")
        self.config = config or ServerConfig()
        
        # Initialize components
        self.health_checker = health_checker or HealthChecker()
        self.metrics_collector = metrics_collector or MetricsCollector()
        
        # Server state
        self.startup_time = datetime.utcnow()
        self.app = None
        self.server = None
        
        # Setup FastAPI app
        self._setup_app()
        
        self.logger.info(
            "Monitoring server initialized",
            extra={
                "host": self.config.host,
                "port": self.config.port,
                "cors_enabled": self.config.enable_cors
            }
        )
    
    def _setup_app(self) -> None:
        """Setup FastAPI application with all endpoints and middleware."""
        # Create FastAPI app with lifespan management
        self.app = FastAPI(
            title="GLM Code Review Bot Monitoring",
            description="Monitoring and metrics API for GLM Code Review Bot",
            version="1.0.0",
            lifespan=self._lifespan
        )
        
        # Add CORS middleware if enabled
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins or ["*"],
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Add request logging middleware
        self.app.middleware("http")(self._log_requests)
        
        # Setup endpoints
        self._setup_health_endpoints()
        self._setup_metrics_endpoints()
        self._setup_admin_endpoints()
        self._setup_info_endpoints()
    
    @asynccontextmanager
    async def _lifespan(self, app: FastAPI):
        """Manage application lifecycle."""
        # Startup
        self.logger.info("Monitoring server starting up")
        self.metrics_collector.start_collection()
        
        yield
        
        # Shutdown
        self.logger.info("Monitoring server shutting down")
        self.metrics_collector.stop_collection()
    
    async def _log_requests(self, request: Request, call_next):
        """Log incoming requests with timing."""
        start_time = datetime.utcnow()
        
        response = await call_next(request)
        
        duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
        
        self.logger.info(
            f"HTTP {request.method} {request.url.path} - {response.status_code}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
                "user_agent": request.headers.get("user-agent", ""),
                "remote_addr": request.client.host if request.client else "unknown"
            }
        )
        
        return response
    
    def _setup_health_endpoints(self) -> None:
        """Setup health check endpoints."""
        
        @self.app.get("/health", summary="Basic health check")
        async def health_check():
            """
            Basic health check endpoint.
            
            Returns minimal health information for load balancers
            and monitoring systems.
            """
            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds()
            }
        
        @self.app.get("/health/detailed", summary="Detailed health check")
        async def detailed_health_check():
            """
            Detailed health check with all subsystems.
            
            Returns comprehensive health information from all
            registered health checkers.
            """
            try:
                health_data = await self.health_checker.check_all()
                return health_data
            except Exception as e:
                self.logger.error(
                    "Detailed health check failed",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Health check failed: {str(e)}"
                )
        
        @self.app.get("/health/checker/{checker_name}", summary="Specific health check")
        async def specific_health_check(checker_name: str):
            """
            Run a specific health check by name.
            
            Args:
                checker_name: Name of the health checker to run
            """
            try:
                result = await self.health_checker.check_single(checker_name)
                if result is None:
                    raise HTTPException(
                        status_code=404,
                        detail=f"Health checker not found: {checker_name}"
                    )
                return result.to_dict()
            except Exception as e:
                self.logger.error(
                    f"Health check failed for {checker_name}",
                    extra={
                        "checker_name": checker_name,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Health check failed: {str(e)}"
                )
        
        @self.app.get("/health/status", summary="Health checker status")
        async def health_status():
            """
            Get status of all health checkers without running checks.
            
            Returns information about available health checkers
            and their configuration.
            """
            try:
                status_data = await self.health_checker.get_status_summary()
                return status_data
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get health status: {str(e)}"
                )
    
    def _setup_metrics_endpoints(self) -> None:
        """Setup metrics endpoints."""
        
        @self.app.get("/metrics", summary="Application metrics")
        async def get_metrics():
            """
            Get comprehensive application metrics.
            
            Returns all collected metrics including API statistics,
            token usage, and system metrics.
            """
            try:
                metrics_data = self.metrics_collector.get_all_metrics()
                return metrics_data
            except Exception as e:
                self.logger.error(
                    "Failed to get metrics",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get metrics: {str(e)}"
                )
        
        @self.app.get("/metrics/prometheus", summary="Prometheus metrics")
        async def get_prometheus_metrics(registry: str = "main"):
            """
            Get metrics in Prometheus format.
            
            Args:
                registry: Name of the metrics registry to export
            """
            try:
                # Validate registry name
                available_registries = self.metrics_collector.list_available_registries()
                if registry not in available_registries:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Unknown registry: {registry}. Available: {available_registries}"
                    )
                
                metrics_data = self.metrics_collector.get_prometheus_metrics(registry)
                
                return PlainTextResponse(
                    content=metrics_data,
                    media_type="text/plain; version=0.0.4; charset=utf-8"
                )
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(
                    f"Failed to get Prometheus metrics for {registry}",
                    extra={
                        "registry": registry,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get Prometheus metrics: {str(e)}"
                )
        
        @self.app.get("/metrics/registries", summary="Available metric registries")
        async def list_registries():
            """
            List all available metrics registries.
            
            Returns a list of available Prometheus metrics registries
            that can be exported.
            """
            try:
                registries = self.metrics_collector.list_available_registries()
                return {
                    "registries": registries,
                    "count": len(registries)
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to list registries: {str(e)}"
                )
    
    def _setup_admin_endpoints(self) -> None:
        """Setup administrative endpoints."""
        
        @self.app.post("/admin/reset-metrics", summary="Reset metrics")
        async def reset_metrics(api_name: Optional[str] = None):
            """
            Reset collected metrics.
            
            Args:
                api_name: Specific API to reset, or None for all
            """
            try:
                self.metrics_collector.reset_metrics(api_name)
                return {
                    "message": "Metrics reset successfully",
                    "api_name": api_name or "all"
                }
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to reset metrics: {str(e)}"
                )
        
        @self.app.get("/admin/config", summary="Server configuration")
        async def get_config():
            """
            Get server configuration (sanitized).
            
            Returns current server configuration with sensitive
            information redacted.
            """
            try:
                config_data = {
                    "host": self.config.host,
                    "port": self.config.port,
                    "log_level": self.config.log_level,
                    "cors_enabled": self.config.enable_cors,
                    "cors_origins": self.config.cors_origins,
                    "workers": self.config.workers,
                    "reload": self.config.reload,
                    "startup_time": self.startup_time.isoformat()
                }
                return config_data
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get configuration: {str(e)}"
                )
    
    def _setup_info_endpoints(self) -> None:
        """Setup information endpoints."""
        
        @self.app.get("/", summary="Server information")
        async def server_info():
            """
            Get server information and available endpoints.
            
            Returns basic server information and links to
            available monitoring endpoints.
            """
            return {
                "name": "GLM Code Review Bot Monitoring Server",
                "version": "1.0.0",
                "status": "running",
                "startup_time": self.startup_time.isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds(),
                "endpoints": {
                    "health": "/health",
                    "detailed_health": "/health/detailed",
                    "specific_health": "/health/checker/{name}",
                    "health_status": "/health/status",
                    "metrics": "/metrics",
                    "prometheus_metrics": "/metrics/prometheus?registry={name}",
                    "metric_registries": "/metrics/registries",
                    "admin_reset_metrics": "/admin/reset-metrics",
                    "admin_config": "/admin/config"
                }
            }
        
        @self.app.get("/docs", include_in_schema=False)
        async def docs():
            """Redirect to FastAPI docs."""
            return JSONResponse(
                content={
                    "message": "FastAPI documentation",
                    "swagger_ui": "/docs",
                    "redoc": "/redoc"
                }
            )
    
    async def start_server(self) -> None:
        """Start the monitoring server."""
        try:
            config = uvicorn.Config(
                app=self.app,
                host=self.config.host,
                port=self.config.port,
                log_level=self.config.log_level,
                workers=self.config.workers if not self.config.reload else 1,  # reload incompatible with workers
                reload=self.config.reload
            )
            
            self.server = uvicorn.Server(config)
            
            self.logger.info(
                "Starting monitoring server",
                extra={
                    "host": self.config.host,
                    "port": self.config.port,
                    "workers": self.config.workers,
                    "reload": self.config.reload
                }
            )
            
            await self.server.serve()
            
        except Exception as e:
            self.logger.error(
                "Failed to start monitoring server",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise
    
    async def stop_server(self) -> None:
        """Stop the monitoring server."""
        if self.server:
            self.logger.info("Stopping monitoring server")
            self.server.should_exit = True
            await self.server.shutdown()

    async def shutdown(self) -> None:
        """Trigger graceful shutdown of uvicorn server (alias for stop_server)."""
        if self.server:
            self.logger.info("Triggering monitoring server shutdown")
            self.server.should_exit = True
            await self.server.shutdown()

    def run(self) -> None:
        """Run the monitoring server synchronously."""
        try:
            uvicorn.run(
                app=self.app,
                host=self.config.host,
                port=self.config.port,
                log_level=self.config.log_level,
                workers=self.config.workers if not self.config.reload else 1,
                reload=self.config.reload
            )
        except KeyboardInterrupt:
            self.logger.info("Monitoring server stopped by user")
        except Exception as e:
            self.logger.error(
                "Monitoring server crashed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise
    
    def get_app(self) -> FastAPI:
        """
        Get the FastAPI application instance.
        
        Returns:
            FastAPI application instance for external hosting
        """
        return self.app


# Factory function for easy server creation
def create_monitoring_server(
    health_checker: Optional[HealthChecker] = None,
    metrics_collector: Optional[MetricsCollector] = None,
    config: Optional[ServerConfig] = None
) -> MonitoringServer:
    """
    Factory function to create a monitoring server.
    
    Args:
        health_checker: Optional health checker instance
        metrics_collector: Optional metrics collector instance
        config: Optional server configuration
        
    Returns:
        Configured monitoring server instance
    """
    return MonitoringServer(
        health_checker=health_checker,
        metrics_collector=metrics_collector,
        config=config
    )


# Configuration from settings
def create_server_from_settings() -> MonitoringServer:
    """
    Create monitoring server from application settings.
    
    Returns:
        Monitoring server configured from settings
    """
    # Extract server config from settings if available
    server_config = ServerConfig()
    
    if settings:
        # Map settings to server config
        if hasattr(settings, 'monitoring_host'):
            server_config.host = settings.monitoring_host
        if hasattr(settings, 'monitoring_port'):
            server_config.port = settings.monitoring_port
        if hasattr(settings, 'log_level'):
            server_config.log_level = settings.log_level.lower()
    
    # Create components
    health_checker = HealthChecker()
    metrics_collector = MetricsCollector()
    
    return MonitoringServer(
        health_checker=health_checker,
        metrics_collector=metrics_collector,
        config=server_config
    )


# CLI entry point
async def main():
    """CLI entry point for running the monitoring server."""
    import sys
    
    try:
        # Create and run server
        server = create_server_from_settings()
        await server.start_server()
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())