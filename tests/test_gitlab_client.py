"""
Unit tests for GitLab API client
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from gitlab_client import GitLabClient
from utils.exceptions import GitLabAPIError, RetryExhaustedError


class TestGitLabClient:
    """Test cases for GitLabClient class"""

    @pytest.fixture
    def client(self, monkeypatch):
        """Create a GitLabClient instance with mocked environment variables"""
        monkeypatch.setenv("GITLAB_TOKEN", "test_token")
        monkeypatch.setenv("GITLAB_API_URL", "https://gitlab.example.com/api/v4")
        monkeypatch.setenv("CI_PROJECT_ID", "123")
        monkeypatch.setenv("CI_MERGE_REQUEST_IID", "456")
        return GitLabClient()

    def test_init_with_env_vars(self, client):
        """Test client initialization with environment variables"""
        assert client.token == "test_token"
        assert client.api_url == "https://gitlab.example.com/api/v4"
        assert client.project_id == "123"
        assert client.mr_iid == "456"
        assert "Authorization" in client.headers
        assert client.headers["Authorization"] == "Bearer test_token"

    def test_init_with_defaults(self, monkeypatch):
        """Test client initialization with default values"""
        # Test that client works with conftest environment
        client = GitLabClient()
        # Just verify it has a valid URL (conftest sets it to example.com)
        assert "gitlab" in client.api_url
        assert client.api_url.endswith("/api/v4")

    @patch('gitlab_client.requests.get')
    def test_get_merge_request_diff_success(self, mock_get, client):
        """Test successful diff retrieval"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = [
            {
                "old_path": "src/example.py",
                "new_path": "src/example.py",
                "diff": "@@ -10,7 +10,7 @@\n-def old_function():\n+def new_function():\n     pass"
            },
            {
                "old_path": "README.md",
                "new_path": "README.md",
                "diff": "@@ -1,3 +1,4 @@\n # Project Title\n\n+New line\n"
            }
        ]
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        result = client.get_merge_request_diff()

        # Verify API call
        expected_url = "https://gitlab.example.com/api/v4/projects/123/merge_requests/456/diffs"
        mock_get.assert_called_once_with(expected_url, headers=client.headers)

        # Verify formatted diff
        assert "--- src/example.py" in result
        assert "+++ src/example.py" in result
        assert "def old_function():" in result
        assert "def new_function():" in result
        assert "--- README.md" in result
        assert "+++ README.md" in result
        assert "New line" in result

    @patch('gitlab_client.requests.get')
    def test_get_merge_request_diff_api_error(self, mock_get, client):
        """Test handling of GitLab API errors during diff retrieval"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        mock_get.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            client.get_merge_request_diff()

        assert "Failed to fetch merge request diff" in str(exc_info.value)

    @patch('gitlab_client.requests.post')
    def test_post_comment_success(self, mock_post, client):
        """Test successful comment posting"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {"id": 789, "body": "Test comment"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        body = "Test comment"
        result = client.post_comment(body)

        # Verify API call
        expected_url = "https://gitlab.example.com/api/v4/projects/123/merge_requests/456/notes"
        mock_post.assert_called_once_with(
            expected_url,
            json={"body": "Test comment"},
            headers=client.headers
        )

        # Verify return value
        assert result["id"] == 789
        assert result["body"] == "Test comment"

    @patch('gitlab_client.requests.post')
    def test_post_comment_with_position(self, mock_post, client):
        """Test comment posting with position data"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {"id": 789, "body": "Test comment"}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        body = "Test comment"
        position = {
            "base_sha": "abc123",
            "start_sha": "def456",
            "head_sha": "ghi789",
            "position_type": "text",
            "new_path": "src/example.py",
            "new_line": 42
        }
        result = client.post_comment(body, position)

        # Verify API call - should use /discussions endpoint for positioned comments
        expected_url = "https://gitlab.example.com/api/v4/projects/123/merge_requests/456/discussions"
        mock_post.assert_called_once_with(
            expected_url,
            json={"body": "Test comment", "position": position},
            headers=client.headers
        )

        # Verify return value
        assert result["id"] == 789
        assert result["body"] == "Test comment"

    @patch('gitlab_client.requests.post')
    def test_post_comment_api_error(self, mock_post, client):
        """Test handling of GitLab API errors during comment posting"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        mock_post.return_value = mock_response

        with pytest.raises(Exception) as exc_info:
            client.post_comment("Test comment")

        assert "Failed to post comment" in str(exc_info.value)

    def test_format_diff_empty(self, client):
        """Test formatting of empty diff"""
        result = client._format_diff([])
        assert result == ""

    def test_format_diff_single_file(self, client):
        """Test formatting of single file diff"""
        diffs = [
            {
                "old_path": "src/example.py",
                "new_path": "src/example.py",
                "diff": "@@ -10,7 +10,7 @@\n-def old_function():\n+def new_function():\n     pass"
            }
        ]

        result = client._format_diff(diffs)

        expected = "--- src/example.py\n+++ src/example.py\n@@ -10,7 +10,7 @@\n-def old_function():\n+def new_function():\n     pass"
        assert result == expected

    def test_format_diff_multiple_files(self, client):
        """Test formatting of multiple file diffs"""
        diffs = [
            {
                "old_path": "src/example.py",
                "new_path": "src/example.py",
                "diff": "@@ -10,7 +10,7 @@\n-def old_function():\n+def new_function():\n     pass"
            },
            {
                "old_path": "README.md",
                "new_path": "README.md",
                "diff": "@@ -1,3 +1,4 @@\n # Project Title\n\n+New line\n"
            }
        ]

        result = client._format_diff(diffs)

        lines = result.split("\n")
        assert "--- src/example.py" in lines
        assert "+++ src/example.py" in lines
        assert "--- README.md" in lines
        assert "+++ README.md" in lines