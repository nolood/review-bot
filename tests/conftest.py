"""
Configuration for pytest test suite
"""
import os
import sys
from pathlib import Path

# Add src to path
project_root = Path(__file__).parent.parent
src_path = project_root / "src"
sys.path.insert(0, str(src_path))

# Set test environment variables BEFORE importing anything from src
os.environ.update({
    "CI": "true",
    "CI_PROJECT_ID": "123",
    "CI_MERGE_REQUEST_IID": "456",
    "GITLAB_TOKEN": "test_token",
    "GITLAB_API_URL": "https://gitlab.example.com/api/v4",
    "GLM_API_KEY": "test_glm_api_key",
    "GLM_API_URL": "https://api.example.com/v1/chat/completions"
})