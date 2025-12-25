from src.utils.retry import api_retry, RetryExhaustedError
from src.utils.exceptions import GitLabAPIError
import requests

@api_retry
def gitlab_like_function():
    try:
        # Simulate what happens in GitLab client
        response = Mock()
        response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        response.raise_for_status()  # This will raise HTTPError
    except requests.exceptions.RequestException as e:
        # This is what GitLab client does - catches and re-raises as GitLabAPIError
        raise GitLabAPIError(f"Failed to fetch: {str(e)}")

from unittest.mock import Mock

try:
    gitlab_like_function()
    print("No exception raised - retry not working")
except RetryExhaustedError as e:
    print(f"RetryExhaustedError raised as expected: {e}")
except Exception as e:
    print(f"Other exception raised: {type(e).__name__}: {e}")
