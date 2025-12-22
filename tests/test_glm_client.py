"""
Unit tests for GLM API client
"""
import json
import pytest
from unittest.mock import Mock, patch, MagicMock
import requests

from src.glm_client import GLMClient
from src.utils.exceptions import GLMAPIError


class TestGLMClient:
    """Test cases for GLMClient class"""

    @pytest.fixture
    def client(self, monkeypatch):
        """Create a GLMClient instance with mocked environment variables"""
        monkeypatch.setenv("GLM_API_KEY", "test_glm_api_key")
        monkeypatch.setenv("GLM_API_URL", "https://api.example.com/v1/chat/completions")
        return GLMClient()

    def test_init_with_env_vars(self, client):
        """Test client initialization with environment variables"""
        assert client.api_key == "test_glm_api_key"
        assert client.api_url == "https://api.example.com/v1/chat/completions"

    def test_init_with_default(self, monkeypatch):
        """Test client initialization with default API URL"""
        monkeypatch.setenv("GLM_API_KEY", "test_glm_api_key")
        monkeypatch.delenv("GLM_API_URL", raising=False)
        client = GLMClient()
        assert client.api_url == "https://api.z.ai/api/paas/v4/chat/completions"

    @patch('src.glm_client.requests.post')
    def test_analyze_code_success(self, mock_post, client):
        """Test successful code analysis"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "comments": [
                                {
                                    "file": "src/example.py",
                                    "line": 42,
                                    "comment": "Consider using list comprehension",
                                    "type": "suggestion",
                                    "severity": "low"
                                }
                            ]
                        })
                    }
                }
            ],
            "usage": {
                "prompt_tokens": 1234,
                "completion_tokens": 567,
                "total_tokens": 1801
            }
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        diff = "--- a/src/example.py\n+++ b/src/example.py\n@@ -42,3 +42,3 @@\n old_code\n new_code"
        result = client.analyze_code(diff)

        # Verify API call
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        
        assert kwargs["json"]["model"] == "glm-4"
        assert len(kwargs["json"]["messages"]) == 2
        assert kwargs["json"]["messages"][0]["role"] == "system"
        assert kwargs["json"]["messages"][1]["role"] == "user"
        assert "temperature" in kwargs["json"]
        assert kwargs["json"]["temperature"] == 0.3

        # Verify parsed response
        assert "comments" in result
        assert len(result["comments"]) == 1
        assert result["comments"][0]["file"] == "src/example.py"
        assert result["comments"][0]["line"] == 42
        assert "list comprehension" in result["comments"][0]["comment"]

    @patch('src.glm_client.requests.post')
    def test_analyze_code_with_custom_prompt(self, mock_post, client):
        """Test code analysis with custom prompt"""
        # Mock API response
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "comments": [
                                {
                                    "comment": "Security issue found",
                                    "severity": "high"
                                }
                            ]
                        })
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        custom_prompt = "Focus on security vulnerabilities only"
        diff = "some diff content"
        client.analyze_code(diff, custom_prompt)

        # Verify API call included custom prompt
        args, kwargs = mock_post.call_args
        user_message = kwargs["json"]["messages"][1]
        assert custom_prompt in user_message["content"]
        assert diff in user_message["content"]

    @patch('src.glm_client.requests.post')
    def test_analyze_code_api_error(self, mock_post, client):
        """Test handling of GLM API errors"""
        mock_response = Mock()
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError("API Error")
        mock_post.return_value = mock_response

        with pytest.raises(GLMAPIError) as exc_info:
            client.analyze_code("some diff")

        assert "Failed to analyze code" in str(exc_info.value)

    @patch('src.glm_client.requests.post')
    def test_analyze_code_malformed_response(self, mock_post, client):
        """Test handling of malformed API response"""
        # Mock API response with invalid JSON in content
        mock_response = Mock()
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is not valid JSON"
                    }
                }
            ]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        result = client.analyze_code("some diff")

        # Should fall back to text format
        assert "comments" in result
        assert len(result["comments"]) == 1
        assert result["comments"][0]["comment"] == "This is not valid JSON"
        assert result["comments"][0]["severity"] == "medium"

    @patch('src.glm_client.requests.post')
    def test_analyze_code_missing_choices(self, mock_post, client):
        """Test handling of response missing choices"""
        # Mock API response without choices
        mock_response = Mock()
        mock_response.json.return_value = {}
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response

        with pytest.raises(GLMAPIError) as exc_info:
            client.analyze_code("some diff")

        assert "Invalid response format" in str(exc_info.value)

    def test_get_default_prompt(self, client):
        """Test default prompt generation"""
        prompt = client._get_default_prompt()
        assert "Analyze this code" in prompt
        assert "JSON" in prompt
        assert "comments" in prompt
        assert "file" in prompt
        assert "line" in prompt
        assert "severity" in prompt

    def test_parse_response_valid_json(self, client):
        """Test parsing valid JSON response"""
        response = {
            "choices": [
                {
                    "message": {
                        "content": json.dumps({
                            "comments": [
                                {
                                    "file": "test.py",
                                    "line": 10,
                                    "comment": "Test comment",
                                    "severity": "low"
                                }
                            ]
                        })
                    }
                }
            ]
        }

        result = client._parse_response(response)

        assert "comments" in result
        assert len(result["comments"]) == 1
        assert result["comments"][0]["file"] == "test.py"
        assert result["comments"][0]["line"] == 10

    def test_parse_response_invalid_json(self, client):
        """Test parsing response with invalid JSON"""
        response = {
            "choices": [
                {
                    "message": {
                        "content": "This is not valid JSON"
                    }
                }
            ]
        }

        result = client._parse_response(response)

        assert "comments" in result
        assert len(result["comments"]) == 1
        assert result["comments"][0]["comment"] == "This is not valid JSON"
        assert result["comments"][0]["severity"] == "medium"

    def test_parse_response_missing_content(self, client):
        """Test parsing response with missing content"""
        response = {
            "choices": [
                {
                    "message": {}
                }
            ]
        }

        with pytest.raises(GLMAPIError) as exc_info:
            client._parse_response(response)

        assert "Invalid response format" in str(exc_info.value)

    def test_estimate_tokens(self, client):
        """Test token estimation for different content types"""
        # Test code content
        code = "def hello_world():\n    print('Hello, World!')\n    return True"
        tokens = client._estimate_tokens(code, "code")
        assert tokens > 0
        
        # Test text content
        text = "This is a sample text with some words and sentences for testing token estimation."
        tokens = client._estimate_tokens(text, "text")
        assert tokens > 0
        
        # Test diff content
        diff = "@@ -1,3 +1,4 @@\n def hello_world():\n-    print('Hello')\n+    print('Hello, World!')\n     return True"
        tokens = client._estimate_tokens(diff, "diff")
        assert tokens > 0