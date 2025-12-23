    class RetryExhaustedError(Exception):
        def __init__(self, message, attempts=None, last_error=None):
            details = {}
            if attempts is not None:
                details["attempts"] = attempts
            if last_error is not None:
                details["last_error_type"] = type(last_error).__name__
                details["last_error_message"] = str(last_error)
            super().__init__(message, error_code="RETRY_EXHAUSTED_ERROR", details=details)
