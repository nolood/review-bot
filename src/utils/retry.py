"""
Retry mechanism with exponential backoff for the GLM Code Review Bot.

Provides a decorator and utilities for retrying operations
with configurable backoff strategies.
"""

import time
import random
import functools
import asyncio
from typing import Any, Optional, List, Tuple, Dict, Callable, Type, TypeVar, Union

T = TypeVar('T')
from dataclasses import dataclass

try:
    from .exceptions import ReviewBotError, RetryExhaustedError
except ImportError:
    # Fallback for circular import during development
    class ReviewBotError(Exception):
        pass
    
    class RetryExhaustedError(ReviewBotError):
        def __init__(self, message: str, attempts: Optional[int] = None, last_error: Optional[Exception] = None):
            super().__init__(message)
            self.attempts = attempts
            self.last_error = last_error


@dataclass
class RetryConfig:
    """
    Configuration for retry behavior.
    
    Attributes:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay between retries in seconds
        backoff_factor: Multiplier for exponential backoff
        max_delay: Maximum delay between retries in seconds
        jitter: Whether to add random jitter to delays
        retryable_exceptions: Exception types that should trigger retries
        non_retryable_exceptions: Exception types that should NOT trigger retries
    """
    max_retries: int = 3
    initial_delay: float = 1.0
    backoff_factor: float = 2.0
    max_delay: float = 60.0
    jitter: bool = True
    retryable_exceptions: Tuple[Type[Exception], ...] = (
        ReviewBotError,
        ConnectionError,
        TimeoutError,
        OSError,
    )
    non_retryable_exceptions: Tuple[Type[Exception], ...] = (
        ValueError,
        TypeError,
        KeyError,
        NotImplementedError,
    )
    
    def should_retry(self, exception: Exception) -> bool:
        """
        Determine if an exception should trigger a retry.
        
        Args:
            exception: Exception to evaluate
            
        Returns:
            True if the exception should trigger a retry
        """
        # Check non-retryable exceptions first
        for exc_type in self.non_retryable_exceptions:
            if isinstance(exception, exc_type):
                return False
        
        # Check retryable exceptions
        for exc_type in self.retryable_exceptions:
            if isinstance(exception, exc_type):
                return True
        
        # Default to not retrying unknown exceptions
        return False
    
    def calculate_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given retry attempt.
        
        Args:
            attempt: Current attempt number (0-based)
            
        Returns:
            Delay in seconds
        """
        # Calculate exponential backoff
        delay = self.initial_delay * (self.backoff_factor ** attempt)
        
        # Apply maximum delay limit
        delay = min(delay, self.max_delay)
        
        # Add jitter if enabled
        if self.jitter:
            # Add ±25% random jitter
            jitter_factor = 0.75 + (random.random() * 0.5)
            delay *= jitter_factor
        
        return delay


class RetryState:
    """
    State tracking for retry operations.
    
    Maintains information about retry attempts,
    timing, and error history.
    """
    
    def __init__(self, config: RetryConfig):
        """Initialize retry state."""
        self.config = config
        self.attempts: List[Tuple[int, float, Exception]] = []  # (attempt, timestamp, exception)
        self.start_time = time.time()
    
    def record_attempt(self, attempt: int, exception: Exception):
        """Record a failed attempt."""
        self.attempts.append((attempt, time.time(), exception))
    
    def should_continue(self, attempt: int, exception: Exception) -> bool:
        """Determine if retrying should continue."""
        return attempt < self.config.max_retries and self.config.should_retry(exception)
    
    def get_next_delay(self, attempt: int) -> float:
        """Get delay for next retry attempt."""
        return self.config.calculate_delay(attempt)
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of retry attempts."""
        return {
            "total_attempts": len(self.attempts) + 1,  # +1 for final successful attempt
            "failed_attempts": len(self.attempts),
            "duration_seconds": time.time() - self.start_time,
            "config": {
                "max_retries": self.config.max_retries,
                "initial_delay": self.config.initial_delay,
                "backoff_factor": self.config.backoff_factor
            }
        }


def retry_with_backoff(
    config: Optional[RetryConfig] = None,
    **config_kwargs
):
    """
    Decorator for retrying functions with exponential backoff.
    
    Can be used with both sync and async functions.
    
    Args:
        config: Retry configuration (if not provided, created from config_kwargs)
        **config_kwargs: Configuration options for RetryConfig
        
    Returns:
        Decorated function that retries on failures
    """
    if config is None:
        config = RetryConfig(**config_kwargs)
    
    def decorator(func):
        """Decorator function."""
        
        if asyncio.iscoroutinefunction(func):
            # Async function wrapper
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs) -> T:
                """Async wrapper with retry logic."""
                state = RetryState(config)
                last_exception = None
                
                for attempt in range(config.max_retries + 1):
                    try:
                        if attempt > 0:
                            delay = state.get_next_delay(attempt - 1)
                            await asyncio.sleep(delay)
                        
                        result = await func(*args, **kwargs)
                        
                        # Log successful retry if we had attempts
                        if attempt > 0:
                            from .logger import get_logger
                            logger = get_logger("retry")
                            logger.info(
                                f"Operation succeeded after {attempt} retries",
                                extra={
                                    "function": func.__name__,
                                    "attempts": attempt + 1,
                                    "duration_seconds": time.time() - state.start_time
                                }
                            )
                        
                        return result
                        
                    except Exception as e:
                        last_exception = e
                        
                        # Record the attempt
                        state.record_attempt(attempt, e)
                        
                        # Check if we should retry
                        if not state.should_continue(attempt + 1, e):
                            break
                        
                        # Log retry attempt
                        from .logger import get_logger
                        logger = get_logger("retry")
                        logger.warning(
                            f"Operation failed, retrying... (attempt {attempt + 1}/{config.max_retries})",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": config.max_retries,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                                "next_delay": state.get_next_delay(attempt + 1) if attempt < config.max_retries else None
                            }
                        )
                
                # All retries exhausted
                raise RetryExhaustedError(
                    f"Operation '{func.__name__}' failed after {config.max_retries} retries",
                    attempts=config.max_retries,
                    last_error=last_exception
                )
            
            return async_wrapper
        
        else:
            # Sync function wrapper
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs) -> T:
                """Sync wrapper with retry logic."""
                state = RetryState(config)
                last_exception = None
                
                for attempt in range(config.max_retries + 1):
                    try:
                        if attempt > 0:
                            delay = state.get_next_delay(attempt - 1)
                            time.sleep(delay)
                        
                        result = func(*args, **kwargs)
                        
                        # Log successful retry if we had attempts
                        if attempt > 0:
                            from .logger import get_logger
                            logger = get_logger("retry")
                            logger.info(
                                f"Operation succeeded after {attempt} retries",
                                extra={
                                    "function": func.__name__,
                                    "attempts": attempt + 1,
                                    "duration_seconds": time.time() - state.start_time
                                }
                            )
                        
                        return result
                        
                    except Exception as e:
                        last_exception = e
                        
                        # Record the attempt
                        state.record_attempt(attempt, e)
                        
                        # Check if we should retry
                        if not state.should_continue(attempt + 1, e):
                            break
                        
                        # Log retry attempt
                        from .logger import get_logger
                        logger = get_logger("retry")
                        logger.warning(
                            f"Operation failed, retrying... (attempt {attempt + 1}/{config.max_retries})",
                            extra={
                                "function": func.__name__,
                                "attempt": attempt + 1,
                                "max_retries": config.max_retries,
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                                "next_delay": state.get_next_delay(attempt + 1) if attempt < config.max_retries else None
                            }
                        )
                
                # All retries exhausted
                raise RetryExhaustedError(
                    f"Operation '{func.__name__}' failed after {config.max_retries} retries",
                    attempts=config.max_retries,
                    last_error=last_exception
                )
            
            return sync_wrapper
    
    return decorator


# Default retry configurations for different use cases
API_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=1.0,
    backoff_factor=2.0,
    max_delay=30.0,
    jitter=True,
    retryable_exceptions=(
        ReviewBotError,
        ConnectionError,
        TimeoutError,
        OSError,
    ),
    non_retryable_exceptions=(
        ValueError,
        TypeError,
        KeyError,
    )
)

DIFF_PROCESSING_RETRY_CONFIG = RetryConfig(
    max_retries=2,
    initial_delay=0.5,
    backoff_factor=1.5,
    max_delay=5.0,
    jitter=False,
    retryable_exceptions=(
        ReviewBotError,
    ),
    non_retryable_exceptions=(
        ValueError,
        TypeError,
    )
)

COMMENT_PUBLISH_RETRY_CONFIG = RetryConfig(
    max_retries=3,
    initial_delay=2.0,
    backoff_factor=2.0,
    max_delay=60.0,
    jitter=True,
    retryable_exceptions=(
        ReviewBotError,
        ConnectionError,
        TimeoutError,
    ),
    non_retryable_exceptions=(
        ValueError,
        TypeError,
        KeyError,
    )
)


# Convenience decorators with pre-configured retry settings
def api_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for API calls with standard retry configuration."""
    return retry_with_backoff(API_RETRY_CONFIG)(func)


def diff_processing_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for diff processing operations with retry configuration."""
    return retry_with_backoff(DIFF_PROCESSING_RETRY_CONFIG)(func)


def comment_publish_retry(func: Callable[..., T]) -> Callable[..., T]:
    """Decorator for comment publishing with retry configuration."""
    return retry_with_backoff(COMMENT_PUBLISH_RETRY_CONFIG)(func)