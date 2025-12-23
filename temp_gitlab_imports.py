try:
    from src.config.settings import settings
    from src.utils.exceptions import GitLabAPIError, RetryExhaustedError
    from src.utils.logger import get_logger
    from src.utils.retry import api_retry
except ImportError:
    # Fallback for when running in test environment
    settings = None
    GitLabAPIError = Exception
    
    class RetryExhaustedError(Exception):
        def __init__(self, message, details=None):
            super().__init__(message)
            self.details = details or {}
    
    from src.utils.logger import get_fallback_logger as get_logger
    
    def api_retry(func):
        return func
