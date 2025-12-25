from src.utils.retry import api_retry, RetryExhaustedError
import requests

@api_retry
def test_function():
    raise requests.exceptions.HTTPError("Test error")

try:
    test_function()
    print("No exception raised - retry not working")
except RetryExhaustedError as e:
    print(f"RetryExhaustedError raised as expected: {e}")
except Exception as e:
    print(f"Other exception raised: {type(e).__name__}: {e}")
