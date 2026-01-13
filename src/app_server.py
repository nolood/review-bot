"""
Simplified App Server for GLM Code Review Bot.

This module provides a production-ready FastAPI server that integrates:
- Review bot functionality with async processing
- Basic monitoring and health checks
- Web interface for triggering and managing reviews
- Background task processing with proper lifecycle management
"""

import asyncio
import signal
import sys
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

# Check if FastAPI is available
try:
    from fastapi import FastAPI, HTTPException, Request, Response, BackgroundTasks
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.gzip import GZipMiddleware
    from fastapi.responses import JSONResponse, HTMLResponse
    import uvicorn
    
    FASTAPI_AVAILABLE = True
    print("FastAPI available - full server functionality enabled")
except ImportError as e:
    print(f"FastAPI not available: {e}")
    FASTAPI_AVAILABLE = False


# Basic mock models for when FastAPI is not available
class MockBaseModel:
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class MockField:
    def __init__(self, default=None, description=None, **kwargs):
        self.default = default
        self.description = description


def MockValidator(field_name, **kwargs):
    def decorator(func):
        return func
    return decorator


# Try to import app components with fallbacks
try:
    from .config.settings import settings
except ImportError:
    print("Settings not available, using fallback")
    settings = None

try:
    from .utils.logger import get_logger
except ImportError:
    def get_logger(name: str):
        import logging
        return logging.getLogger(name)

try:
    from .review_processor_async import AsyncReviewProcessor, ReviewContext
except ImportError:
    print("Async review processor not available, using fallback")
    AsyncReviewProcessor = None
    ReviewContext = None

try:
    from .config.prompts import ReviewType
except ImportError:
    print("ReviewType not available, using fallback")
    # Fallback enum for ReviewType
    class ReviewType(Enum):
        GENERAL = "general"
        SECURITY = "security"
        PERFORMANCE = "performance"
        CODE_STYLE = "code_style"

try:
    from .client_manager_async import AsyncClientManager
except ImportError:
    print("Async client manager not available, using fallback")
    AsyncClientManager = None

try:
    from .deduplication import CommitTracker, CommentTracker, DeduplicationStrategy
except ImportError:
    CommitTracker = None
    CommentTracker = None
    DeduplicationStrategy = None

try:
    from .webhook.models import NoteWebhookPayload
except ImportError:
    NoteWebhookPayload = None


# Mock components for standalone development
class MockSettings:
    def __init__(self):
        self.gitlab_token = os.getenv("GITLAB_TOKEN", "test_token")
        self.gitlab_api_url = os.getenv("GITLAB_API_URL", "https://gitlab.example.com/api/v4")
        self.project_id = os.getenv("CI_PROJECT_ID", "123")
        self.mr_iid = os.getenv("CI_MERGE_REQUEST_IID", "456")
        self.glm_api_key = os.getenv("GLM_API_KEY", "test_glm_key")
        self.glm_api_url = os.getenv("GLM_API_URL", "https://api.example.com/v1/chat/completions")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.enable_cors = True
        self.cors_origins = ["*"]
        self.server_host = os.getenv("SERVER_HOST", "0.0.0.0")
        self.server_port = int(os.getenv("SERVER_PORT", "8000"))
        self.monitoring_enabled = os.getenv("MONITORING_ENABLED", "true").lower() == "true"
        self.monitoring_port = int(os.getenv("MONITORING_PORT", "8080"))
        self.max_concurrent_reviews = int(os.getenv("MAX_CONCURRENT_REVIEWS", "3"))
        self.review_timeout_seconds = int(os.getenv("REVIEW_TIMEOUT_SECONDS", "300"))
        
    def get_gitlab_headers(self):
        return {"Authorization": f"Bearer {self.gitlab_token}"}
        
    def get_glm_headers(self):
        return {"Authorization": f"Bearer {self.glm_api_key}"}


class MockAsyncReviewProcessor:
    def __init__(self, settings_instance, concurrent_limit=3):
        self.settings = settings_instance
        self.concurrent_limit = concurrent_limit
        
    async def process_review(self, context):
        return {"status": "completed", "comments": []}


class MockAsyncClientManager:
    def __init__(self, settings_instance):
        self.settings = settings_instance
        
    async def initialize(self):
        pass
        
    async def cleanup(self):
        pass


@dataclass
class MockReviewContext:
    project_id: str
    mr_iid: str
    mr_details: Optional[Dict[str, Any]] = None
    diff_summary: Optional[Dict[str, Any]] = None
    processing_stats: Optional[Dict[str, Any]] = field(default_factory=dict)


# Use fallbacks if main components are not available
if settings is None:
    settings = MockSettings()

if AsyncReviewProcessor is None:
    AsyncReviewProcessor = MockAsyncReviewProcessor

if AsyncClientManager is None:
    AsyncClientManager = MockAsyncClientManager

if ReviewContext is None:
    ReviewContext = MockReviewContext


# Simple data models (no complex Pydantic validation)
if FASTAPI_AVAILABLE:
    # Use real models when FastAPI is available
    class ReviewRequest(MockBaseModel):
        def __init__(self, project_id=None, mr_iid=None, force_review=False, **kwargs):
            super().__init__(**kwargs)
            self.project_id = project_id or getattr(settings, 'project_id', '')
            self.mr_iid = mr_iid or getattr(settings, 'mr_iid', '')
            self.force_review = force_review

    class ReviewResponse(MockBaseModel):
        def __init__(self, task_id, status, message, created_at, **kwargs):
            super().__init__(**kwargs)
            self.task_id = task_id
            self.status = status
            self.message = message
            self.created_at = created_at

    class ReviewStatusResponse(MockBaseModel):
        def __init__(self, task_id, status, progress=0.0, message="", started_at=None, completed_at=None, result=None, error=None, **kwargs):
            super().__init__(**kwargs)
            self.task_id = task_id
            self.status = status
            self.progress = progress
            self.message = message
            self.started_at = started_at
            self.completed_at = completed_at
            self.result = result
            self.error = error

    class ServerStatusResponse(MockBaseModel):
        def __init__(self, status, uptime_seconds, version, active_reviews, completed_reviews, failed_reviews, monitoring_enabled, **kwargs):
            super().__init__(**kwargs)
            self.status = status
            self.uptime_seconds = uptime_seconds
            self.version = version
            self.active_reviews = active_reviews
            self.completed_reviews = completed_reviews
            self.failed_reviews = failed_reviews
            self.monitoring_enabled = monitoring_enabled
else:
    # Use mock models when FastAPI is not available
    ReviewRequest = MockBaseModel
    ReviewResponse = MockBaseModel
    ReviewStatusResponse = MockBaseModel
    ServerStatusResponse = MockBaseModel


class TaskStatus(Enum):
    """Task status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ReviewTask:
    """Background review task data."""
    task_id: str
    project_id: str
    mr_iid: str
    status: TaskStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    progress: float = 0.0
    message: str = ""
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    context: Optional[ReviewContext] = None


@dataclass
class ServerConfig:
    """Main server configuration."""
    host: str = "0.0.0.0"
    port: int = 8000
    log_level: str = "info"
    enable_cors: bool = True
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    enable_compression: bool = True
    max_concurrent_reviews: int = 3
    review_timeout_seconds: int = 300
    enable_monitoring: bool = True
    monitoring_port: int = 8080
    workers: int = 1
    reload: bool = False


class AppServer:
    """
    Main application server integrating review bot with monitoring.
    
    This server provides:
    - REST API for review management
    - Background task processing
    - Monitoring integration
    - Web interface for manual operations
    - Production-ready deployment features
    """
    
    def __init__(
        self,
        config: Optional[ServerConfig] = None,
        settings_instance: Optional[Any] = None
    ):
        """
        Initialize the application server.
        
        Args:
            config: Server configuration
            settings_instance: Application settings instance
        """
        self.logger = get_logger("app_server")
        self.config = config or ServerConfig()
        self.settings = settings_instance or settings
        
        # Server state
        self.startup_time = datetime.utcnow()
        self.shutdown_event = asyncio.Event()
        
        # Review task management
        self.active_tasks: Dict[str, ReviewTask] = {}
        self.task_history: List[ReviewTask] = []
        self.max_history_size = 100
        
        # Application components
        self.review_processor: Optional[AsyncReviewProcessor] = None
        self.client_manager: Optional[AsyncClientManager] = None

        # Deduplication components
        self.commit_tracker: Optional[CommitTracker] = None
        self.comment_tracker: Optional[CommentTracker] = None

        # Bot username for discussion resolution
        self.bot_username: Optional[str] = None

        # FastAPI app (only if available)
        self.app = None
        
        # Statistics
        self.stats = {
            "total_reviews": 0,
            "completed_reviews": 0,
            "failed_reviews": 0,
            "active_reviews": 0
        }
        
        # Setup application if FastAPI is available
        if FASTAPI_AVAILABLE:
            self._setup_app()
        else:
            self.logger.warning("FastAPI not available - running in limited mode")
        
        self.logger.info(
            "Application server initialized",
            extra={
                "host": self.config.host,
                "port": self.config.port,
                "monitoring_enabled": self.config.enable_monitoring,
                "max_concurrent_reviews": self.config.max_concurrent_reviews,
                "fastapi_available": FASTAPI_AVAILABLE
            }
        )
    
    def _setup_app(self) -> None:
        """Setup FastAPI application with all endpoints and middleware."""
        if not FASTAPI_AVAILABLE:
            return
            
        # Create FastAPI app with lifespan management
        self.app = FastAPI(
            title="GLM Code Review Bot",
            description="Automated code review bot for GitLab with GLM integration",
            version="1.0.0",
            lifespan=self._lifespan
        )
        
        # Add middleware
        self._setup_middleware()
        
        # Setup endpoints
        self._setup_review_endpoints()
        self._setup_status_endpoints()
        self._setup_webhook_endpoints()
        self._setup_web_interface()
        self._setup_admin_endpoints()
    
    def _setup_middleware(self) -> None:
        """Setup application middleware."""
        if not self.app:
            return
            
        # CORS middleware
        if self.config.enable_cors:
            self.app.add_middleware(
                CORSMiddleware,
                allow_origins=self.config.cors_origins,
                allow_credentials=True,
                allow_methods=["*"],
                allow_headers=["*"],
            )
        
        # Compression middleware
        if self.config.enable_compression:
            self.app.add_middleware(GZipMiddleware, minimum_size=1000)
        
        # Request logging middleware
        self.app.middleware("http")(self._log_requests)
    
    @asynccontextmanager
    async def _lifespan(self, app):
        """Manage application lifecycle."""
        if not FASTAPI_AVAILABLE:
            return
            
        try:
            # Startup
            self.logger.info("Application server starting up")
            await self._startup()
            yield
        finally:
            # Shutdown
            self.logger.info("Application server shutting down")
            await self._shutdown()
    
    async def _startup(self) -> None:
        """Initialize application components."""
        try:
            # Initialize client manager
            self.client_manager = AsyncClientManager(self.settings)
            await self.client_manager.initialize_clients()

            # Initialize review processor
            self.review_processor = AsyncReviewProcessor(
                self.settings,
                concurrent_limit=self.config.max_concurrent_reviews
            )

            # Resolve bot_username once for consistency
            bot_username = getattr(self.settings, 'bot_username', None) or os.getenv('BOT_USERNAME', 'review-bot')
            self.bot_username = bot_username  # Store for use in webhook handlers

            self.logger.info(
                "Bot username configured",
                extra={
                    "bot_username": bot_username,
                    "source": "settings" if getattr(self.settings, 'bot_username', None) else "env/default"
                }
            )

            # Initialize deduplication trackers
            if getattr(self.settings, 'deduplication_enabled', True) and CommitTracker:
                self.commit_tracker = CommitTracker(ttl_seconds=86400)  # 24 hours

                # Get sync gitlab client for CommentTracker
                gitlab_client = await self.client_manager.get_client("gitlab")
                self.comment_tracker = CommentTracker(
                    gitlab_client=gitlab_client,
                    bot_username=bot_username
                )
                self.logger.info("Deduplication trackers initialized")

            # DO NOT setup signal handlers here - let review_bot_server.py handle them
            # to avoid signal handler conflicts during shutdown
            # self._setup_signal_handlers()

            self.logger.info("Application startup completed")
            
        except Exception as e:
            self.logger.error(
                "Application startup failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise
    
    async def _shutdown(self) -> None:
        """Cleanup application resources."""
        try:
            # Signal shutdown
            self.shutdown_event.set()
            
            # Cancel active tasks
            for task_id, task in list(self.active_tasks.items()):
                if task.status == TaskStatus.RUNNING:
                    task.status = TaskStatus.CANCELLED
                    task.completed_at = datetime.utcnow()
                    task.message = "Cancelled due to server shutdown"
                    
                    # Move to history
                    self.active_tasks.pop(task_id, None)
                    self._add_to_history(task)
            
            # Cleanup client manager
            if self.client_manager:
                await self.client_manager.close_all_clients()
            
            self.logger.info("Application shutdown completed")
            
        except Exception as e:
            self.logger.error(
                "Error during shutdown",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
    
    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            self.logger.info(f"Received signal {signum}, initiating graceful shutdown")
            self.shutdown_event.set()
        
        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def _log_requests(self, request, call_next):
        """Log incoming requests with timing."""
        if not FASTAPI_AVAILABLE:
            return None
            
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
    
    def _setup_review_endpoints(self) -> None:
        """Setup review management endpoints."""
        if not self.app:
            return
        
        @self.app.post("/api/v1/reviews")
        async def trigger_review(request_data: Dict[str, Any], background_tasks: BackgroundTasks):
            """Trigger a code review for a merge request."""
            try:
                # Extract request data
                project_id = request_data.get("project_id") or getattr(self.settings, 'project_id', '')
                mr_iid = request_data.get("mr_iid") or getattr(self.settings, 'mr_iid', '')
                force_review = request_data.get("force_review", False)
                
                # Validate request
                if not project_id or not mr_iid:
                    raise HTTPException(
                        status_code=400,
                        detail="Both project_id and mr_iid are required"
                    )
                
                # Check for concurrent review limits
                active_count = sum(
                    1 for task in self.active_tasks.values()
                    if task.status == TaskStatus.RUNNING
                )
                
                if active_count >= self.config.max_concurrent_reviews:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Maximum concurrent reviews ({self.config.max_concurrent_reviews}) reached"
                    )
                
                # Generate task ID
                task_id = str(uuid.uuid4())
                
                # Create task
                task = ReviewTask(
                    task_id=task_id,
                    project_id=project_id,
                    mr_iid=mr_iid,
                    status=TaskStatus.PENDING,
                    created_at=datetime.utcnow(),
                    message="Review queued for processing"
                )
                
                self.active_tasks[task_id] = task
                self.stats["total_reviews"] += 1
                self.stats["active_reviews"] = active_count + 1
                
                # Add background task
                background_tasks.add_task(
                    self._process_review_background,
                    task_id,
                    project_id,
                    mr_iid,
                    force_review
                )
                
                self.logger.info(
                    "Review triggered",
                    extra={
                        "task_id": task_id,
                        "project_id": project_id,
                        "mr_iid": mr_iid,
                        "force_review": force_review
                    }
                )
                
                return {
                    "task_id": task_id,
                    "status": "pending",
                    "message": "Review queued for processing",
                    "created_at": task.created_at.isoformat()
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(
                    "Failed to trigger review",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to trigger review: {str(e)}"
                )
        
        @self.app.get("/api/v1/reviews/{task_id}/status")
        async def get_review_status(task_id: str):
            """Get the status of a review task."""
            try:
                # Check active tasks
                if task_id in self.active_tasks:
                    task = self.active_tasks[task_id]
                else:
                    # Check history
                    task = next(
                        (t for t in self.task_history if t.task_id == task_id),
                        None
                    )
                    
                    if not task:
                        raise HTTPException(
                            status_code=404,
                            detail=f"Review task not found: {task_id}"
                        )
                
                return {
                    "task_id": task.task_id,
                    "status": task.status.value,
                    "progress": task.progress,
                    "message": task.message,
                    "started_at": task.started_at.isoformat() if task.started_at else None,
                    "completed_at": task.completed_at.isoformat() if task.completed_at else None,
                    "result": task.result,
                    "error": task.error
                }
                
            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(
                    f"Failed to get review status for {task_id}",
                    extra={
                        "task_id": task_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get review status: {str(e)}"
                )
    
    def _setup_status_endpoints(self) -> None:
        """Setup server status endpoints."""
        if not self.app:
            return
        
        @self.app.get("/api/v1/status")
        async def get_server_status():
            """Get server status and statistics."""
            try:
                uptime_seconds = (datetime.utcnow() - self.startup_time).total_seconds()
                
                return {
                    "status": "running",
                    "uptime_seconds": uptime_seconds,
                    "version": "1.0.0",
                    "active_reviews": self.stats["active_reviews"],
                    "completed_reviews": self.stats["completed_reviews"],
                    "failed_reviews": self.stats["failed_reviews"],
                    "monitoring_enabled": self.config.enable_monitoring
                }
                
            except Exception as e:
                self.logger.error(
                    "Failed to get server status",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get server status: {str(e)}"
                )
        
        @self.app.get("/health")
        async def health_check():
            """Basic health check for load balancers."""
            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "uptime_seconds": (datetime.utcnow() - self.startup_time).total_seconds()
            }

    def _setup_webhook_endpoints(self) -> None:
        """Setup webhook endpoints for GitLab integration."""
        if not self.app:
            return

        @self.app.post("/webhook/gitlab")
        async def gitlab_webhook(request: Request, background_tasks: BackgroundTasks):
            """
            Handle GitLab webhook events for merge requests.

            This endpoint:
            1. Validates webhook signature
            2. Parses and filters events
            3. Checks if commit already reviewed (deduplication)
            4. Queues background task for review
            5. Returns 202 Accepted with task_id
            """
            try:
                # Check if webhooks are enabled
                if not getattr(self.settings, 'webhook_enabled', False):
                    return JSONResponse(
                        status_code=200,
                        content={"message": "Webhooks are disabled"}
                    )

                # Validate webhook signature
                gitlab_token = request.headers.get("X-Gitlab-Token")
                expected_token = getattr(self.settings, 'webhook_secret', '')

                if not gitlab_token or gitlab_token != expected_token:
                    self.logger.warning(
                        "Invalid webhook signature",
                        extra={
                            "remote_addr": request.client.host if request.client else "unknown",
                            "token_present": bool(gitlab_token)
                        }
                    )
                    raise HTTPException(
                        status_code=401,
                        detail="Invalid webhook signature"
                    )

                # Parse webhook payload
                try:
                    payload = await request.json()
                except Exception as e:
                    self.logger.error(
                        "Failed to parse webhook payload",
                        extra={
                            "error_type": type(e).__name__,
                            "error_message": str(e)
                        }
                    )
                    raise HTTPException(
                        status_code=400,
                        detail="Invalid JSON payload"
                    )

                # Extract event type and data
                event_type = payload.get("object_kind")

                # Handle NOTE webhook for discussion resolution
                if event_type == "note":
                    return await self._handle_note_webhook(payload, request)

                if event_type != "merge_request":
                    return JSONResponse(
                        status_code=200,
                        content={"message": f"Ignored event type: {event_type}"}
                    )

                # Extract merge request data
                mr_data = payload.get("object_attributes", {})
                action = mr_data.get("action")
                project = payload.get("project", {})

                project_id = str(project.get("id", ""))
                mr_iid = str(mr_data.get("iid", ""))

                if not project_id or not mr_iid:
                    raise HTTPException(
                        status_code=400,
                        detail="Missing project_id or mr_iid in webhook payload"
                    )

                # Check trigger actions
                webhook_trigger_actions = getattr(self.settings, 'webhook_trigger_actions', ["open", "update", "reopen"])
                if action not in webhook_trigger_actions:
                    return JSONResponse(
                        status_code=200,
                        content={"message": f"Ignored action: {action}"}
                    )

                # Check draft status
                if getattr(self.settings, 'webhook_skip_draft', True):
                    if mr_data.get("work_in_progress", False) or mr_data.get("draft", False):
                        return JSONResponse(
                            status_code=200,
                            content={"message": "Skipped: MR is draft or WIP"}
                        )

                # Check WIP status in title
                if getattr(self.settings, 'webhook_skip_wip', True):
                    title = mr_data.get("title", "")
                    if title.lower().startswith("wip:") or "[wip]" in title.lower():
                        return JSONResponse(
                            status_code=200,
                            content={"message": "Skipped: MR title contains WIP"}
                        )

                # Check labels
                labels = [label.get("title") for label in mr_data.get("labels", [])]

                required_labels = getattr(self.settings, 'webhook_required_labels', [])
                if required_labels:
                    if not any(label in labels for label in required_labels):
                        return JSONResponse(
                            status_code=200,
                            content={"message": f"Skipped: Required labels not found"}
                        )

                excluded_labels = getattr(self.settings, 'webhook_excluded_labels', [])
                if excluded_labels:
                    if any(label in labels for label in excluded_labels):
                        return JSONResponse(
                            status_code=200,
                            content={"message": f"Skipped: Excluded label found"}
                        )

                # Check deduplication
                if getattr(self.settings, 'deduplication_enabled', True) and self.commit_tracker:
                    commit_sha = mr_data.get("last_commit", {}).get("id")
                    if commit_sha and self.commit_tracker.is_commit_reviewed(project_id, mr_iid, commit_sha):
                        self.logger.info(
                            "Skipping already reviewed commit",
                            extra={"project_id": project_id, "mr_iid": mr_iid, "commit_sha": commit_sha[:8]}
                        )
                        return JSONResponse(
                            status_code=200,
                            content={"message": f"Skipped: Commit {commit_sha[:8]} already reviewed"}
                        )

                # Check for concurrent review limits
                active_count = sum(
                    1 for task in self.active_tasks.values()
                    if task.status == TaskStatus.RUNNING
                )

                if active_count >= self.config.max_concurrent_reviews:
                    raise HTTPException(
                        status_code=429,
                        detail=f"Maximum concurrent reviews ({self.config.max_concurrent_reviews}) reached"
                    )

                # Generate task ID
                task_id = str(uuid.uuid4())

                # Create task
                task = ReviewTask(
                    task_id=task_id,
                    project_id=project_id,
                    mr_iid=mr_iid,
                    status=TaskStatus.PENDING,
                    created_at=datetime.utcnow(),
                    message="Review queued from webhook"
                )

                self.active_tasks[task_id] = task
                self.stats["total_reviews"] += 1
                self.stats["active_reviews"] = active_count + 1

                # Queue background review
                background_tasks.add_task(
                    self._process_webhook_review,
                    task_id,
                    project_id,
                    mr_iid,
                    payload
                )

                self.logger.info(
                    "Webhook review queued",
                    extra={
                        "task_id": task_id,
                        "project_id": project_id,
                        "mr_iid": mr_iid,
                        "action": action,
                        "event_type": event_type
                    }
                )

                return JSONResponse(
                    status_code=202,
                    content={
                        "task_id": task_id,
                        "status": "accepted",
                        "message": "Review queued for processing",
                        "created_at": task.created_at.isoformat()
                    }
                )

            except HTTPException:
                raise
            except Exception as e:
                self.logger.error(
                    "Webhook processing failed",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                raise HTTPException(
                    status_code=500,
                    detail=f"Internal server error: {str(e)}"
                )

    async def _process_webhook_review(
        self,
        task_id: str,
        project_id: str,
        mr_iid: str,
        webhook_payload: Dict[str, Any]
    ) -> None:
        """
        Process webhook review in background.

        Args:
            task_id: Unique task identifier
            project_id: GitLab project ID
            mr_iid: Merge request IID
            webhook_payload: Original webhook payload for context
        """
        task = self.active_tasks.get(task_id)
        if not task:
            self.logger.error(f"Task not found for webhook review: {task_id}")
            return

        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            task.message = "Starting webhook review"
            task.progress = 0.1

            # Create review context
            task.context = ReviewContext(
                project_id=project_id,
                mr_iid=mr_iid
            )

            # Cleanup old bot comments before new review
            if getattr(self.settings, 'deduplication_enabled', True) and self.comment_tracker:
                try:
                    cleanup_result = await self.comment_tracker.cleanup_old_comments(
                        project_id=project_id,
                        mr_iid=mr_iid,
                        strategy=DeduplicationStrategy.DELETE_ALL
                    )
                    self.logger.info(
                        "Old comments cleanup completed",
                        extra={
                            "project_id": project_id,
                            "mr_iid": mr_iid,
                            "deleted": cleanup_result.deleted_count,
                            "failed": cleanup_result.failed_count
                        }
                    )
                except Exception as e:
                    self.logger.warning(f"Comment cleanup failed, continuing: {e}")

            # Update progress
            task.progress = 0.2
            task.message = "Analyzing merge request from webhook"

            # Process review with timeout
            result = await asyncio.wait_for(
                self.review_processor.process_merge_request(
                    dry_run=False,
                    review_type=ReviewType.GENERAL,
                    project_id=project_id,
                    mr_iid=mr_iid
                ),
                timeout=self.config.review_timeout_seconds
            )

            # Mark commit as reviewed
            if getattr(self.settings, 'deduplication_enabled', True) and self.commit_tracker:
                commit_sha = webhook_payload.get("object_attributes", {}).get("last_commit", {}).get("id")
                if commit_sha:
                    comment_count = result.get("stats", {}).get("total_comments_generated", 0) if isinstance(result, dict) else 0
                    self.commit_tracker.mark_commit_reviewed(project_id, mr_iid, commit_sha, comment_count)
                    self.logger.info(f"Marked commit {commit_sha[:8]} as reviewed")

            # Update progress
            task.progress = 0.9
            task.message = "Finalizing webhook review"

            # Complete task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            task.message = "Webhook review completed successfully"
            task.result = result

            # Update statistics
            self.stats["completed_reviews"] += 1
            self.stats["active_reviews"] = max(0, self.stats["active_reviews"] - 1)

            # Move to history
            self.active_tasks.pop(task_id, None)
            self._add_to_history(task)

            self.logger.info(
                "Webhook review completed",
                extra={
                    "task_id": task_id,
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "duration_seconds": (task.completed_at - task.started_at).total_seconds()
                }
            )

        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.progress = 0.0
            task.message = "Webhook review timed out"
            task.error = f"Review exceeded timeout of {self.config.review_timeout_seconds} seconds"

            self.stats["failed_reviews"] += 1
            self.stats["active_reviews"] = max(0, self.stats["active_reviews"] - 1)

            self.active_tasks.pop(task_id, None)
            self._add_to_history(task)

            self.logger.error(
                "Webhook review timed out",
                extra={
                    "task_id": task_id,
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "timeout_seconds": self.config.review_timeout_seconds
                }
            )

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.progress = 0.0
            task.message = "Webhook review failed"
            task.error = str(e)

            self.stats["failed_reviews"] += 1
            self.stats["active_reviews"] = max(0, self.stats["active_reviews"] - 1)

            self.active_tasks.pop(task_id, None)
            self._add_to_history(task)

            self.logger.error(
                "Webhook review failed",
                extra={
                    "task_id": task_id,
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )

    async def _handle_note_webhook(
        self,
        payload: Dict[str, Any],
        request: Request
    ) -> JSONResponse:
        """
        Handle NOTE webhook for discussion resolution.

        This method processes note webhooks to automatically resolve discussions
        when a user posts a comment with the text "done".

        Args:
            payload: The webhook payload dictionary
            request: The FastAPI request object

        Returns:
            JSONResponse with the processing result
        """
        try:
            # Check if NoteWebhookPayload model is available
            if NoteWebhookPayload is None:
                self.logger.warning("NoteWebhookPayload model not available")
                return JSONResponse(
                    status_code=200,
                    content={"message": "Note webhook model not available"}
                )

            # Parse payload into NoteWebhookPayload model
            try:
                note_payload = NoteWebhookPayload(**payload)
            except Exception as e:
                self.logger.warning(
                    "Failed to parse note webhook payload",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    }
                )
                return JSONResponse(
                    status_code=200,
                    content={"message": "Invalid note webhook payload"}
                )

            # Validate it's a MR discussion note
            if not note_payload.is_merge_request_note:
                return JSONResponse(
                    status_code=200,
                    content={"message": "Ignored: Not a merge request note"}
                )

            # Check if it's part of a discussion
            if not note_payload.is_discussion_note:
                return JSONResponse(
                    status_code=200,
                    content={"message": "Ignored: Not a discussion note"}
                )

            # Check if merge_request object exists
            if note_payload.merge_request is None:
                return JSONResponse(
                    status_code=200,
                    content={"message": "Ignored: No merge request data in payload"}
                )

            # Check if note body is "done" (case-insensitive)
            note_body = note_payload.note_body.strip().lower()
            if note_body != "done":
                return JSONResponse(
                    status_code=200,
                    content={"message": f"Ignored: Note body is not 'done' (got: '{note_body}')"}
                )

            # Extract required data
            project_id = str(note_payload.project_id)
            mr_iid = str(note_payload.merge_request.iid)
            discussion_id = note_payload.discussion_id

            # Validate discussion_id is present
            if not discussion_id:
                self.logger.warning("Missing discussion_id in note webhook payload")
                return JSONResponse(
                    status_code=200,
                    content={"message": "Ignored: Missing discussion_id"}
                )

            self.logger.info(
                "Processing note webhook for discussion resolution",
                extra={
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "discussion_id": discussion_id,
                    "note_body": note_payload.note_body
                }
            )

            # Get gitlab_client from client_manager
            if not self.client_manager:
                self.logger.error("Client manager not available")
                return JSONResponse(
                    status_code=500,
                    content={"message": "Client manager not initialized"}
                )

            try:
                gitlab_client = await self.client_manager.get_client("gitlab")
            except Exception as e:
                self.logger.error(
                    "Failed to get GitLab client",
                    extra={
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                return JSONResponse(
                    status_code=500,
                    content={"message": f"Failed to get GitLab client: {str(e)}"}
                )

            # Check if discussion was created by the bot
            bot_username = getattr(self, 'bot_username', None) or getattr(self.settings, 'bot_username', None) or os.getenv('BOT_USERNAME', 'review-bot')

            try:
                discussion = await gitlab_client.get_discussion(
                    discussion_id=discussion_id,
                    project_id=project_id,
                    mr_iid=mr_iid
                )

                notes = discussion.get("notes", [])
                if notes:
                    first_author = notes[0].get("author", {}).get("username", "")
                    if first_author != bot_username:
                        self.logger.info(
                            f"Discussion not created by bot, skipping resolution",
                            extra={
                                "discussion_creator": first_author,
                                "expected_bot": bot_username,
                                "discussion_id": discussion_id
                            }
                        )
                        return JSONResponse(
                            status_code=200,
                            content={
                                "message": f"Note ignored: discussion not created by bot (author: {first_author})"
                            }
                        )
            except Exception as e:
                self.logger.warning(f"Failed to verify discussion ownership: {e}")
                return JSONResponse(
                    status_code=200,
                    content={"message": f"Note ignored: could not verify discussion ownership"}
                )

            # Call resolve_discussion() on the client
            try:
                result = await gitlab_client.resolve_discussion(
                    discussion_id=discussion_id,
                    resolved=True,
                    project_id=project_id,
                    mr_iid=mr_iid
                )

                self.logger.info(
                    "Discussion resolved successfully",
                    extra={
                        "project_id": project_id,
                        "mr_iid": mr_iid,
                        "discussion_id": discussion_id,
                        "result": result
                    }
                )

                return JSONResponse(
                    status_code=200,
                    content={
                        "message": "Discussion resolved successfully",
                        "discussion_id": discussion_id,
                        "project_id": project_id,
                        "mr_iid": mr_iid
                    }
                )

            except Exception as e:
                self.logger.error(
                    "Failed to resolve discussion",
                    extra={
                        "project_id": project_id,
                        "mr_iid": mr_iid,
                        "discussion_id": discussion_id,
                        "error_type": type(e).__name__,
                        "error_message": str(e)
                    },
                    exc_info=True
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "message": f"Failed to resolve discussion: {str(e)}",
                        "discussion_id": discussion_id
                    }
                )

        except Exception as e:
            self.logger.error(
                "Note webhook processing failed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            return JSONResponse(
                status_code=500,
                content={"message": f"Internal server error: {str(e)}"}
            )

    def _setup_web_interface(self) -> None:
        """Setup web interface endpoints."""
        if not self.app:
            return
        
        @self.app.get("/", response_class=HTMLResponse)
        async def web_interface():
            """Main web interface for triggering and monitoring reviews."""
            html_content = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>GLM Code Review Bot</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1">
                <style>
                    body { font-family: Arial, sans-serif; margin: 40px; background: #f5f5f5; }
                    .container { max-width: 800px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                    h1 { color: #333; text-align: center; margin-bottom: 30px; }
                    .form-group { margin-bottom: 20px; }
                    label { display: block; margin-bottom: 5px; font-weight: bold; }
                    input { width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-size: 16px; }
                    button { background: #007bff; color: white; padding: 12px 24px; border: none; border-radius: 4px; cursor: pointer; font-size: 16px; }
                    button:hover { background: #0056b3; }
                    .status { margin-top: 30px; padding: 20px; background: #f8f9fa; border-radius: 4px; }
                    .task-item { border-left: 4px solid #007bff; padding: 10px; margin: 10px 0; background: white; }
                    .task-completed { border-left-color: #28a745; }
                    .task-failed { border-left-color: #dc3545; }
                    .task-running { border-left-color: #ffc107; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 GLM Code Review Bot</h1>
                    
                    <form id="reviewForm">
                        <div class="form-group">
                            <label for="projectId">Project ID:</label>
                            <input type="text" id="projectId" name="projectId" value="{project_id}" required>
                        </div>
                        <div class="form-group">
                            <label for="mrIid">Merge Request IID:</label>
                            <input type="text" id="mrIid" name="mrIid" value="{mr_iid}" required>
                        </div>
                        <div class="form-group">
                            <label>
                                <input type="checkbox" id="forceReview" name="forceReview">
                                Force review even if recently processed
                            </label>
                        </div>
                        <button type="submit">Start Review</button>
                    </form>
                    
                    <div class="status">
                        <h3>Recent Reviews</h3>
                        <div id="reviewsList">Loading...</div>
                    </div>
                </div>
                
                <script>
                    // Load reviews on page load
                    loadReviews();
                    
                    // Handle form submission
                    document.getElementById('reviewForm').addEventListener('submit', async (e) => {
                        e.preventDefault();
                        
                        const formData = new FormData(e.target);
                        const data = {
                            project_id: formData.get('projectId'),
                            mr_iid: formData.get('mrIid'),
                            force_review: formData.get('forceReview') === 'on'
                        };
                        
                        try {
                            const response = await fetch('/api/v1/reviews', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                },
                                body: JSON.stringify(data)
                            });
                            
                            const result = await response.json();
                            
                            if (response.ok) {
                                alert('Review started successfully! Task ID: ' + result.task_id);
                                loadReviews(); // Refresh reviews list
                            } else {
                                alert('Error: ' + result.detail);
                            }
                        } catch (error) {
                            alert('Network error: ' + error.message);
                        }
                    });
                    
                    async function loadReviews() {
                        try {
                            const response = await fetch('/api/v1/reviews?limit=10');
                            const data = await response.json();
                            
                            const reviewsList = document.getElementById('reviewsList');
                            
                            if (data.tasks && data.tasks.length === 0) {
                                reviewsList.innerHTML = '<p>No reviews found.</p>';
                                return;
                            }
                            
                            // For now, show a simple message
                            reviewsList.innerHTML = '<p>Server is running. Reviews will appear here.</p>';
                        } catch (error) {
                            document.getElementById('reviewsList').innerHTML = '<p>Error loading reviews.</p>';
                        }
                    }
                </script>
            </body>
            </html>
            """.format(
                project_id=getattr(self.settings, 'project_id', ''),
                mr_iid=getattr(self.settings, 'mr_iid', '')
            )
            
            return HTMLResponse(content=html_content)
    
    def _setup_admin_endpoints(self) -> None:
        """Setup administrative endpoints."""
        if not self.app:
            return
        
        @self.app.get("/api/v1/admin/config")
        async def get_config():
            """Get server configuration (sanitized)."""
            try:
                config_data = {
                    "host": self.config.host,
                    "port": self.config.port,
                    "log_level": self.config.log_level,
                    "cors_enabled": self.config.enable_cors,
                    "compression_enabled": self.config.enable_compression,
                    "max_concurrent_reviews": self.config.max_concurrent_reviews,
                    "review_timeout_seconds": self.config.review_timeout_seconds,
                    "monitoring_enabled": self.config.enable_monitoring,
                    "monitoring_port": self.config.monitoring_port,
                    "startup_time": self.startup_time.isoformat()
                }
                return config_data
                
            except Exception as e:
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to get configuration: {str(e)}"
                )
        
        @self.app.post("/api/v1/admin/shutdown")
        async def shutdown_server():
            """Initiate graceful server shutdown."""
            # Schedule shutdown after response is sent
            asyncio.create_task(self._delayed_shutdown())
            
            return {
                "message": "Server shutdown initiated",
                "timestamp": datetime.utcnow().isoformat()
            }
    
    def _add_to_history(self, task: ReviewTask) -> None:
        """Add task to history with size limit."""
        self.task_history.append(task)
        
        # Maintain history size limit
        if len(self.task_history) > self.max_history_size:
            self.task_history.pop(0)
    
    async def _process_review_background(
        self,
        task_id: str,
        project_id: str,
        mr_iid: str,
        force_review: bool
    ) -> None:
        """Process review in background."""
        task = self.active_tasks.get(task_id)
        if not task:
            self.logger.error(f"Task not found for background processing: {task_id}")
            return
        
        try:
            # Update task status
            task.status = TaskStatus.RUNNING
            task.started_at = datetime.utcnow()
            task.message = "Starting review process"
            task.progress = 0.1
            
            # Create review context
            task.context = ReviewContext(
                project_id=project_id,
                mr_iid=mr_iid
            )

            # Update progress
            task.progress = 0.2
            task.message = "Analyzing merge request"

            # Process review with timeout
            result = await asyncio.wait_for(
                self.review_processor.process_merge_request(
                    dry_run=False,
                    review_type=ReviewType.GENERAL,
                    project_id=project_id,
                    mr_iid=mr_iid
                ),
                timeout=self.config.review_timeout_seconds
            )
            
            # Update progress
            task.progress = 0.9
            task.message = "Finalizing review results"
            
            # Complete task
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.utcnow()
            task.progress = 1.0
            task.message = "Review completed successfully"
            task.result = result
            
            # Update statistics
            self.stats["completed_reviews"] += 1
            self.stats["active_reviews"] = max(0, self.stats["active_reviews"] - 1)
            
            # Move to history
            self.active_tasks.pop(task_id, None)
            self._add_to_history(task)
            
            self.logger.info(
                "Review completed successfully",
                extra={
                    "task_id": task_id,
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "duration_seconds": (task.completed_at - task.started_at).total_seconds()
                }
            )
            
        except asyncio.TimeoutError:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.progress = 0.0
            task.message = "Review timed out"
            task.error = f"Review exceeded timeout of {self.config.review_timeout_seconds} seconds"
            
            self.stats["failed_reviews"] += 1
            self.stats["active_reviews"] = max(0, self.stats["active_reviews"] - 1)
            
            self.active_tasks.pop(task_id, None)
            self._add_to_history(task)
            
            self.logger.error(
                "Review timed out",
                extra={
                    "task_id": task_id,
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "timeout_seconds": self.config.review_timeout_seconds
                }
            )
            
        except Exception as e:
            task.status = TaskStatus.FAILED
            task.completed_at = datetime.utcnow()
            task.progress = 0.0
            task.message = "Review failed"
            task.error = str(e)
            
            self.stats["failed_reviews"] += 1
            self.stats["active_reviews"] = max(0, self.stats["active_reviews"] - 1)
            
            self.active_tasks.pop(task_id, None)
            self._add_to_history(task)
            
            self.logger.error(
                "Review failed",
                extra={
                    "task_id": task_id,
                    "project_id": project_id,
                    "mr_iid": mr_iid,
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
    
    async def _delayed_shutdown(self) -> None:
        """Delay shutdown to allow response to be sent."""
        await asyncio.sleep(0.1)
        self.shutdown_event.set()

    async def shutdown(self) -> None:
        """Trigger graceful shutdown of uvicorn server."""
        if hasattr(self, 'server') and self.server:
            self.logger.info("Triggering server shutdown")
            self.server.should_exit = True
            await self.server.shutdown()

    async def start_server(self) -> None:
        """Start application server."""
        if not FASTAPI_AVAILABLE:
            self.logger.error("FastAPI not available - cannot start server")
            return
            
        try:
            config = uvicorn.Config(
                app=self.app,
                host=self.config.host,
                port=self.config.port,
                log_level=self.config.log_level,
                workers=self.config.workers if not self.config.reload else 1,
                reload=self.config.reload
            )

            # Store as instance variable for graceful shutdown
            self.server = uvicorn.Server(config)
            
            self.logger.info(
                "Starting application server",
                extra={
                    "host": self.config.host,
                    "port": self.config.port,
                    "workers": self.config.workers,
                    "reload": self.config.reload,
                    "monitoring_port": self.config.monitoring_port if self.config.enable_monitoring else None
                }
            )

            await self.server.serve()
            
        except Exception as e:
            self.logger.error(
                "Failed to start application server",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise
    
    def run(self) -> None:
        """Run application server synchronously."""
        if not FASTAPI_AVAILABLE:
            self.logger.error("FastAPI not available - cannot run server")
            return
            
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
            self.logger.info("Application server stopped by user")
        except Exception as e:
            self.logger.error(
                "Application server crashed",
                extra={
                    "error_type": type(e).__name__,
                    "error_message": str(e)
                },
                exc_info=True
            )
            raise
    
    def get_app(self):
        """Get the FastAPI application instance."""
        return self.app


# Factory functions for easy server creation
def create_app_server(
    config: Optional[ServerConfig] = None,
    settings_instance: Optional[Any] = None
) -> AppServer:
    """Factory function to create an application server."""
    return AppServer(config=config, settings_instance=settings_instance)


def create_server_from_settings() -> AppServer:
    """Create application server from settings."""
    # Extract server config from settings
    server_config = ServerConfig()
    
    # Map settings to server config
    if hasattr(settings, 'server_host'):
        server_config.host = settings.server_host
    if hasattr(settings, 'server_port'):
        server_config.port = settings.server_port
    if hasattr(settings, 'log_level'):
        server_config.log_level = settings.log_level.lower()
    if hasattr(settings, 'enable_cors'):
        server_config.enable_cors = settings.enable_cors
    if hasattr(settings, 'cors_origins'):
        server_config.cors_origins = settings.cors_origins
    if hasattr(settings, 'max_concurrent_reviews'):
        server_config.max_concurrent_reviews = settings.max_concurrent_reviews
    if hasattr(settings, 'review_timeout_seconds'):
        server_config.review_timeout_seconds = settings.review_timeout_seconds
    if hasattr(settings, 'monitoring_enabled'):
        server_config.enable_monitoring = settings.monitoring_enabled
    if hasattr(settings, 'monitoring_port'):
        server_config.monitoring_port = settings.monitoring_port
    
    return AppServer(config=server_config, settings_instance=settings)


# CLI entry point
async def main():
    """CLI entry point for running application server."""
    import argparse
    
    parser = argparse.ArgumentParser(description="GLM Code Review Bot Server")
    parser.add_argument("--host", default="0.0.0.0", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--log-level", default="info", help="Log level")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--no-monitoring", action="store_true", help="Disable monitoring server")
    
    args = parser.parse_args()
    
    try:
        # Create server config
        config = ServerConfig(
            host=args.host,
            port=args.port,
            log_level=args.log_level,
            workers=args.workers,
            reload=args.reload,
            enable_monitoring=not args.no_monitoring
        )
        
        # Create and run server
        server = create_app_server(config=config)
        await server.start_server()
        
    except KeyboardInterrupt:
        print("\nServer stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"Server failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())