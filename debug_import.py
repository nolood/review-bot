print("Starting imports...")

try:
    from src.config.settings import settings
    print("Settings import successful")
    from src.utils.exceptions import GitLabAPIError, RetryExhaustedError
    print("Utils import successful")
    from src.utils.logger import get_logger
    print("Logger import successful")
    from src.utils.retry import api_retry
    print("Retry import successful")
    print("All imports in try block successful")
except ImportError as e:
    print(f"ImportError occurred: {e}")
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
    print("Using fallback imports")

print(f"GitLabAPIError is now: {GitLabAPIError}")
