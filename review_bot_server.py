#!/usr/bin/env python3
"""
Production-ready CLI entry point for GLM Code Review Bot with integrated monitoring.

This module provides a modern Typer-based CLI interface that supports:
- Server mode with monitoring and web interface
- Standalone bot execution
- Health verification and configuration validation
- Environment-specific configurations (dev/staging/prod)
- Comprehensive logging and error handling
- Docker and production deployment optimizations

Features:
- Modern async/await architecture throughout
- Graceful shutdown with signal handling
- Comprehensive monitoring integration
- Production-ready deployment features
- Rich terminal output with progress indicators
- Environment-specific configuration management
"""

import asyncio
import signal
import sys
import os
import json
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Union
from dataclasses import dataclass, field
from enum import Enum

# Add src to path for imports
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Core dependencies
import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.tree import Tree

# Initialize rich console
console = Console()

# Global application state
app_state = {
    "shutdown_requested": False,
    "startup_time": None,
    "logger": None,
    "app_server_available": False,
    "monitoring_available": False,
    "cli_handler_available": False
}

class Environment(str, Enum):
    """Supported deployment environments."""
    DEVELOPMENT = "dev"
    STAGING = "staging"
    PRODUCTION = "prod"

class LogLevel(str, Enum):
    """Supported log levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ReviewType(str, Enum):
    """Supported review types."""
    GENERAL = "general"
    SECURITY = "security"
    PERFORMANCE = "performance"
    CODE_STYLE = "code_style"

@dataclass
class CLIConfig:
    """CLI configuration container."""
    environment: Environment = Environment.DEVELOPMENT
    log_level: LogLevel = LogLevel.INFO
    config_file: Optional[Path] = None
    verbose: bool = False
    dry_run: bool = False
    no_monitoring: bool = False
    no_cors: bool = False
    max_concurrent_reviews: int = 3
    server_host: str = "0.0.0.0"
    server_port: int = 8000
    monitoring_port: int = 8080

def setup_basic_logging():
    """Setup basic logging when utils.logger is not available."""
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def setup_advanced_logging(level: str = "INFO"):
    """Setup advanced logging using utils.logger."""
    try:
        from src.utils.logger import setup_logging
        setup_logging(level=level)
    except ImportError:
        setup_basic_logging()

def get_logger_instance(name: str):
    """Get logger instance with fallback."""
    try:
        from src.utils.logger import get_logger
        return get_logger(name)
    except ImportError:
        import logging
        return logging.getLogger(name)

def setup_signal_handlers():
    """Setup signal handlers for graceful shutdown."""
    def signal_handler(signum, frame):
        console.print(f"\n[yellow]Received signal {signum}, initiating graceful shutdown...[/yellow]")
        app_state["shutdown_requested"] = True
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

def load_dependencies():
    """Load and initialize all dependencies."""
    global app_state
    
    # Try to import configuration and utilities
    try:
        from src.config.settings import Settings, SettingsProtocol, MockSettings
        from src.utils.exceptions import ReviewBotError, ConfigurationError
        
        # Use mock settings for configuration validation
        settings = MockSettings()
        
        # Try to import app server
        try:
            from src.app_server import AppServer, ServerConfig
            app_state["app_server_available"] = True
            app_state["AppServer"] = AppServer
            app_state["ServerConfig"] = ServerConfig
        except ImportError as e:
            console.print(f"[yellow]Warning: App server not available: {e}[/yellow]")
            app_state["AppServer"] = None
            app_state["ServerConfig"] = None
        
        # Try to import monitoring components
        try:
            from src.monitoring.monitoring_server import MonitoringServer, ServerConfig as MonitoringConfig
            from src.monitoring.health_checker import HealthChecker
            from src.monitoring.metrics_collector import MetricsCollector
            app_state["monitoring_available"] = True
            app_state["MonitoringServer"] = MonitoringServer
            app_state["MonitoringConfig"] = MonitoringConfig
            app_state["HealthChecker"] = HealthChecker
            app_state["MetricsCollector"] = MetricsCollector
        except ImportError as e:
            console.print(f"[yellow]Warning: Monitoring components not available: {e}[/yellow]")
            app_state["MonitoringServer"] = None
            app_state["MonitoringConfig"] = None
            app_state["HealthChecker"] = None
            app_state["MetricsCollector"] = None
        
        # Try to import CLI handler
        try:
            from src.cli_handler_async import AsyncCLIHandler
            from src.config.prompts import ReviewType as ConfigReviewType
            app_state["cli_handler_available"] = True
            app_state["AsyncCLIHandler"] = AsyncCLIHandler
            # Map to our ReviewType enum
            app_state["ReviewType"] = ConfigReviewType
        except ImportError as e:
            console.print(f"[yellow]Warning: CLI handler not available: {e}[/yellow]")
            app_state["AsyncCLIHandler"] = None
            app_state["ReviewType"] = None
        
        return True
        
    except ImportError as e:
        console.print(f"[red]Error importing core components: {e}[/red]")
        console.print("[red]Please ensure all dependencies are installed: pip install -r requirements.txt[/red]")
        return False

def create_environment_config(environment: Environment) -> Any:
    """Create environment-specific configuration."""
    try:
        from src.config.settings import Settings
        
        base_config = {
            # Server configuration
            "server_host": "0.0.0.0",
            "server_port": 8000,
            "enable_cors": environment != Environment.PRODUCTION,
            "cors_origins": ["*"] if environment == Environment.DEVELOPMENT else [],
            
            # Monitoring configuration
            "monitoring_enabled": True,
            "monitoring_port": 8080,
            "monitoring_host": "0.0.0.0",
            
            # Performance configuration
            "max_concurrent_reviews": 1 if environment == Environment.DEVELOPMENT else 3,
            "review_timeout_seconds": 300 if environment == Environment.PRODUCTION else 600,
            
            # Logging configuration
            "log_level": "DEBUG" if environment == Environment.DEVELOPMENT else "INFO",
            "log_format": "json" if environment == Environment.PRODUCTION else "text",
            
            # Retry configuration
            "max_retries": 1 if environment == Environment.DEVELOPMENT else 3,
            "retry_delay": 1.0,
            "retry_backoff_factor": 2.0,
            
            # API delays
            "api_request_delay": 0.1 if environment == Environment.DEVELOPMENT else 0.5,
        }
        
        return Settings.from_env(**base_config)
        
    except ImportError:
        # Fallback to mock settings
        from src.config.settings import MockSettings
        return MockSettings()

def validate_configuration(config: CLIConfig) -> None:
    """Validate CLI configuration."""
    # Check required environment variables
    required_vars = ["GITLAB_TOKEN", "GLM_API_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars and not config.dry_run:
        raise ConfigurationError(
            f"Missing required environment variables: {', '.join(missing_vars)}\n"
            "Please set these variables or run with --dry-run"
        )
    
    # Validate port ranges
    if not (1024 <= config.server_port <= 65535):
        raise ConfigurationError(f"Server port must be between 1024 and 65535, got {config.server_port}")
    
    if not (1024 <= config.monitoring_port <= 65535):
        raise ConfigurationError(f"Monitoring port must be between 1024 and 65535, got {config.monitoring_port}")
    
    # Check for port conflicts
    if config.server_port == config.monitoring_port:
        raise ConfigurationError("Server port and monitoring port cannot be the same")

async def run_health_check() -> int:
    """Run comprehensive health check."""
    console.print("[blue]Running health check...[/blue]")
    
    try:
        if not app_state["monitoring_available"]:
            console.print("[yellow]⚠️  Monitoring components not available, performing basic health check[/yellow]")
            return 0
        
        # Initialize components
        HealthChecker = app_state["HealthChecker"]
        health_checker = HealthChecker()
        
        # Run health checks
        health_results = await health_checker.check_all()
        
        # Display results
        table = Table(title="Health Check Results")
        table.add_column("Component", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Message", style="white")
        
        for result in health_results.get("results", []):
            status_style = {
                "healthy": "green",
                "degraded": "yellow", 
                "unhealthy": "red"
            }.get(result.status, "white")
            
            table.add_row(
                result.name,
                f"[{status_style}]{result.status}[/{status_style}]",
                result.message or ""
            )
        
        console.print(table)
        
        # Overall status
        overall_status = health_results.get("overall_status", "unknown")
        if overall_status == "healthy":
            console.print("[green]✅ All systems operational[/green]")
            return 0
        elif overall_status == "degraded":
            console.print("[yellow]⚠️  Some systems degraded[/yellow]")
            return 1
        else:
            console.print("[red]❌ System issues detected[/red]")
            return 2
            
    except Exception as e:
        console.print(f"[red]Health check failed: {e}[/red]")
        return 3

async def validate_config_file(config_file: Optional[Path]) -> int:
    """Validate configuration file."""
    if not config_file:
        console.print("[yellow]No configuration file specified[/yellow]")
        return 0
    
    console.print(f"[blue]Validating configuration file: {config_file}[/blue]")
    
    try:
        if not config_file.exists():
            console.print(f"[red]Configuration file not found: {config_file}[/red]")
            return 1
        
        # Load and validate configuration
        with open(config_file, 'r') as f:
            config_data = json.load(f)
        
        # Try to create settings instance
        from src.config.settings import Settings
        Settings.from_env(**config_data)
        
        console.print("[green]✅ Configuration file is valid[/green]")
        return 0
        
    except json.JSONDecodeError as e:
        console.print(f"[red]Invalid JSON in configuration file: {e}[/red]")
        return 1
    except Exception as e:
        console.print(f"[red]Configuration validation failed: {e}[/red]")
        return 1

# Create Typer application
app = typer.Typer(
    name="review-bot-server",
    help="🤖 GLM Code Review Bot with Integrated Monitoring",
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=False
)

@app.command()
def start_server(
    environment: Environment = typer.Option(
        Environment.DEVELOPMENT,
        "--env", "-e",
        help="Deployment environment"
    ),
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="Server host address"
    ),
    port: int = typer.Option(
        8000,
        "--port", "-p",
        help="Server port"
    ),
    monitoring_port: int = typer.Option(
        8080,
        "--monitoring-port",
        help="Monitoring server port"
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.INFO,
        "--log-level",
        help="Logging level"
    ),
    workers: int = typer.Option(
        1,
        "--workers",
        help="Number of worker processes"
    ),
    reload: bool = typer.Option(
        False,
        "--reload",
        help="Enable auto-reload for development"
    ),
    config_file: Optional[Path] = typer.Option(
        None,
        "--config",
        help="Configuration file path"
    ),
    no_monitoring: bool = typer.Option(
        False,
        "--no-monitoring",
        help="Disable monitoring server"
    ),
    no_cors: bool = typer.Option(
        False,
        "--no-cors",
        help="Disable CORS"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
):
    """Start the review bot server with monitoring and web interface."""
    async def _start_server():
        try:
            # Load dependencies
            if not load_dependencies():
                return 1
            
            # Setup logging
            setup_advanced_logging(level=log_level.value if not verbose else LogLevel.DEBUG.value)
            logger = get_logger_instance("server_cli")
            app_state["logger"] = logger
            app_state["startup_time"] = datetime.utcnow()
            
            # Setup signal handlers
            setup_signal_handlers()
            
            if not app_state["app_server_available"]:
                console.print("[red]❌ App server not available. Please check your installation.[/red]")
                return 1
            
            console.print(Panel.fit(
                f"[bold blue]🤖 GLM Code Review Bot Server[/bold blue]\n"
                f"Environment: {environment.value}\n"
                f"Host: {host}:{port}\n"
                f"Monitoring: {'Enabled' if not no_monitoring else 'Disabled'}",
                title="Server Starting"
            ))
            
            # Create configuration
            config = CLIConfig(
                environment=environment,
                log_level=log_level,
                config_file=config_file,
                verbose=verbose,
                no_monitoring=no_monitoring,
                no_cors=no_cors,
                server_host=host,
                server_port=port,
                monitoring_port=monitoring_port
            )
            
            # Validate configuration
            validate_configuration(config)
            
            # Create environment-specific settings
            app_settings = create_environment_config(environment)
            
            # Create server config
            ServerConfig = app_state["ServerConfig"]
            server_config = ServerConfig(
                host=host,
                port=port,
                log_level=log_level.value.lower(),
                enable_cors=not no_cors,
                enable_monitoring=not no_monitoring,
                monitoring_port=monitoring_port,
                workers=workers,
                reload=reload
            )
            
            # Create app server
            AppServer = app_state["AppServer"]
            app_server = AppServer(config=server_config, settings_instance=app_settings)
            
            # Create monitoring server if enabled
            monitoring_server = None
            if not no_monitoring and app_state["monitoring_available"]:
                MonitoringConfig = app_state["MonitoringConfig"]
                monitoring_config = MonitoringConfig(
                    host="0.0.0.0",
                    port=monitoring_port,
                    log_level=log_level.value.lower()
                )
                
                HealthChecker = app_state["HealthChecker"]
                MetricsCollector = app_state["MetricsCollector"]
                MonitoringServer = app_state["MonitoringServer"]
                
                monitoring_server = MonitoringServer(
                    health_checker=HealthChecker(),
                    metrics_collector=MetricsCollector(),
                    config=monitoring_config
                )
            elif not no_monitoring:
                console.print("[yellow]⚠️  Monitoring requested but components not available[/yellow]")
            
            console.print("[green]✅ Server initialized successfully[/green]")
            
            # Start servers
            tasks = []
            
            if monitoring_server:
                console.print(f"[blue]Starting monitoring server on port {monitoring_port}...[/blue]")
                tasks.append(asyncio.create_task(monitoring_server.start_server()))
            
            console.print(f"[blue]Starting application server on port {port}...[/blue]")
            tasks.append(asyncio.create_task(app_server.start_server()))
            
            # Wait for tasks with graceful shutdown
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task_progress = progress.add_task("Server running...", total=None)
                
                # Monitor for shutdown
                while not app_state["shutdown_requested"]:
                    await asyncio.sleep(1)
                    
                    # Check if any task failed
                    for i, task in enumerate(tasks):
                        if task.done() and task.exception():
                            console.print(f"[red]Server task failed: {task.exception()}[/red]")
                            app_state["shutdown_requested"] = True
                            break
                
                progress.update(task_progress, description="Shutting down...")
            
            # Graceful shutdown
            console.print("[yellow]Initiating graceful shutdown...[/yellow]")
            
            # Cancel tasks
            for task in tasks:
                if not task.done():
                    task.cancel()
            
            # Wait for cancellation
            await asyncio.gather(*tasks, return_exceptions=True)
            
            console.print("[green]✅ Server shutdown complete[/green]")
            return 0
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Server interrupted by user[/yellow]")
            return 130
        except Exception as e:
            console.print(f"[red]Server failed: {e}[/red]")
            logger = app_state.get("logger")
            if logger:
                logger.error("Server startup failed", exc_info=True)
            return 1
    
    # Run async function
    return asyncio.run(_start_server())

@app.command()
def run_bot(
    review_type: str = typer.Option(
        ReviewType.GENERAL.value,
        "--review-type", "-t",
        help="Type of code review to perform"
    ),
    project_id: Optional[str] = typer.Option(
        None,
        "--project-id",
        help="GitLab project ID (overrides CI_PROJECT_ID)"
    ),
    mr_iid: Optional[str] = typer.Option(
        None,
        "--mr-iid",
        help="Merge request IID (overrides CI_MERGE_REQUEST_IID)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Run analysis without publishing comments"
    ),
    concurrent_limit: int = typer.Option(
        3,
        "--concurrent-limit",
        help="Maximum number of concurrent API requests"
    ),
    custom_prompt: Optional[str] = typer.Option(
        None,
        "--custom-prompt",
        help="Custom prompt instructions for GLM analysis"
    ),
    max_chunks: Optional[int] = typer.Option(
        None,
        "--max-chunks",
        help="Maximum number of diff chunks to process"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose logging"
    )
):
    """Run the review bot in standalone mode."""
    async def _run_bot():
        try:
            # Load dependencies
            if not load_dependencies():
                return 1
            
            # Setup logging
            log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
            setup_advanced_logging(level=log_level.value)
            logger = get_logger_instance("bot_cli")
            app_state["logger"] = logger
            
            # Setup signal handlers
            setup_signal_handlers()
            
            if not app_state["cli_handler_available"]:
                console.print("[red]❌ CLI handler not available. Please check your installation.[/red]")
                return 1
            
            console.print(Panel.fit(
                "[bold blue]🤖 GLM Code Review Bot[/bold blue]\n"
                f"Review Type: {review_type}\n"
                f"Mode: {'Dry Run' if dry_run else 'Live'}",
                title="Bot Running"
            ))
            
            # Set environment variables if provided
            if project_id:
                os.environ["CI_PROJECT_ID"] = project_id
            if mr_iid:
                os.environ["CI_MERGE_REQUEST_IID"] = mr_iid
            
            # Create CLI arguments
            cli_args = [
                "--review-type", review_type,
                "--concurrent-limit", str(concurrent_limit),
                "--log-level", log_level.value,
                ("--verbose" if verbose else ""),
                ("--dry-run" if dry_run else "")
            ]
            
            # Add optional arguments
            if custom_prompt:
                cli_args.extend(["--custom-prompt", custom_prompt])
            if max_chunks:
                cli_args.extend(["--max-chunks", str(max_chunks)])
            
            # Filter out empty strings
            cli_args = [arg for arg in cli_args if arg]
            
            # Create and run CLI handler
            AsyncCLIHandler = app_state["AsyncCLIHandler"]
            from src.config.settings import MockSettings
            cli_handler = AsyncCLIHandler(MockSettings())
            
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task_progress = progress.add_task("Processing review...", total=None)
                
                result = await cli_handler.execute(cli_args)
                
                if result == 0:
                    progress.update(task_progress, description="✅ Review completed successfully")
                    console.print("[green]✅ Review completed successfully[/green]")
                else:
                    progress.update(task_progress, description="❌ Review failed")
                    console.print("[red]❌ Review failed[/red]")
            
            return result
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Bot interrupted by user[/yellow]")
            return 130
        except Exception as e:
            console.print(f"[red]Bot failed: {e}[/red]")
            logger = app_state.get("logger")
            if logger:
                logger.error("Bot execution failed", exc_info=True)
            return 1
    
    return asyncio.run(_run_bot())

@app.command()
def health_check(
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output"
    )
):
    """Run comprehensive health verification."""
    async def _health_check():
        try:
            # Load dependencies
            if not load_dependencies():
                return 1
            
            # Setup logging
            log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
            setup_advanced_logging(level=log_level.value)
            logger = get_logger_instance("health_cli")
            
            console.print(Panel.fit(
                "[bold blue]🏥 GLM Code Review Bot Health Check[/bold blue]",
                title="Health Verification"
            ))
            
            return await run_health_check()
            
        except Exception as e:
            console.print(f"[red]Health check failed: {e}[/red]")
            logger = app_state.get("logger")
            if logger:
                logger.error("Health check failed", exc_info=True)
            return 1
    
    return asyncio.run(_health_check())

@app.command()
def validate_config(
    config_file: Optional[Path] = typer.Option(
        None,
        "--config", "-c",
        help="Configuration file to validate"
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose", "-v",
        help="Enable verbose output"
    )
):
    """Validate configuration and environment."""
    async def _validate_config():
        try:
            # Load dependencies
            if not load_dependencies():
                return 1
            
            # Setup logging
            log_level = LogLevel.DEBUG if verbose else LogLevel.INFO
            setup_advanced_logging(level=log_level.value)
            logger = get_logger_instance("config_cli")
            
            console.print(Panel.fit(
                "[bold blue]⚙️  Configuration Validation[/bold blue]",
                title="Config Check"
            ))
            
            # Validate configuration file
            config_result = await validate_config_file(config_file)
            
            # Validate environment
            console.print("[blue]Validating environment variables...[/blue]")
            
            required_vars = ["GITLAB_TOKEN", "GLM_API_KEY"]
            optional_vars = ["CI_PROJECT_ID", "CI_MERGE_REQUEST_IID", "GITLAB_API_URL"]
            
            table = Table(title="Environment Variables")
            table.add_column("Variable", style="cyan")
            table.add_column("Status", style="green")
            table.add_column("Value", style="white")
            
            for var in required_vars:
                value = os.getenv(var, "")
                status = "[green]✅ Set[/green]" if value else "[red]❌ Missing[/red]"
                display_value = "***" if "TOKEN" in var or "KEY" in var else value
                table.add_row(var, status, display_value)
            
            for var in optional_vars:
                value = os.getenv(var, "")
                status = "[green]✅ Set[/green]" if value else "[yellow]⚠️  Not set[/yellow]"
                display_value = value[:20] + "..." if len(value) > 20 else value
                table.add_row(var, status, display_value)
            
            console.print(table)
            
            # Overall result
            if config_result == 0:
                console.print("[green]✅ Configuration validation passed[/green]")
                return 0
            else:
                console.print("[red]❌ Configuration validation failed[/red]")
                return 1
                
        except Exception as e:
            console.print(f"[red]Configuration validation failed: {e}[/red]")
            logger = app_state.get("logger")
            if logger:
                logger.error("Configuration validation failed", exc_info=True)
            return 1
    
    return asyncio.run(_validate_config())

@app.command()
def monitor_mode(
    host: str = typer.Option(
        "0.0.0.0",
        "--host",
        help="Monitoring server host"
    ),
    port: int = typer.Option(
        8080,
        "--port", "-p",
        help="Monitoring server port"
    ),
    log_level: LogLevel = typer.Option(
        LogLevel.INFO,
        "--log-level",
        help="Logging level"
    )
):
    """Run monitoring server only (no review bot functionality)."""
    async def _monitor_mode():
        try:
            # Load dependencies
            if not load_dependencies():
                return 1
            
            # Setup logging
            setup_advanced_logging(level=log_level.value)
            logger = get_logger_instance("monitor_cli")
            app_state["logger"] = logger
            
            # Setup signal handlers
            setup_signal_handlers()
            
            if not app_state["monitoring_available"]:
                console.print("[red]❌ Monitoring components not available. Please check your installation.[/red]")
                return 1
            
            console.print(Panel.fit(
                "[bold blue]📊 GLM Code Review Bot Monitoring[/bold blue]\n"
                f"Host: {host}:{port}",
                title="Monitoring Mode"
            ))
            
            # Create monitoring configuration
            MonitoringConfig = app_state["MonitoringConfig"]
            monitoring_config = MonitoringConfig(
                host=host,
                port=port,
                log_level=log_level.value.lower()
            )
            
            # Create components
            HealthChecker = app_state["HealthChecker"]
            MetricsCollector = app_state["MetricsCollector"]
            MonitoringServer = app_state["MonitoringServer"]
            
            # Create and start monitoring server
            monitoring_server = MonitoringServer(
                health_checker=HealthChecker(),
                metrics_collector=MetricsCollector(),
                config=monitoring_config
            )
            
            console.print("[green]✅ Monitoring server initialized[/green]")
            console.print(f"[blue]Starting monitoring server on {host}:{port}...[/blue]")
            
            # Run server with graceful shutdown
            await monitoring_server.start_server()
            
            console.print("[green]✅ Monitoring server shutdown complete[/green]")
            return 0
            
        except KeyboardInterrupt:
            console.print("\n[yellow]Monitoring server interrupted by user[/yellow]")
            return 130
        except Exception as e:
            console.print(f"[red]Monitoring server failed: {e}[/red]")
            logger = app_state.get("logger")
            if logger:
                logger.error("Monitoring server failed", exc_info=True)
            return 1
    
    return asyncio.run(_monitor_mode())

@app.command()
def version():
    """Show version information."""
    console.print(Panel.fit(
        "[bold blue]🤖 GLM Code Review Bot[/bold blue]\n"
        "Version: 1.0.0\n"
        "Python: 3.11+\n"
        "Async: Yes\n"
        "Monitoring: Yes\n"
        "Production Ready: Yes",
        title="Version Information"
    ))

def main():
    """Main CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
    except Exception as e:
        console.print(f"[red]CLI failed: {e}[/red]")
        sys.exit(1)

if __name__ == "__main__":
    main()