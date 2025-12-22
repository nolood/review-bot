"""
Test fixtures and utilities for the review bot tests
"""
import pytest


@pytest.fixture
def sample_diff():
    """Sample GitLab diff for testing"""
    return {
        "old_path": "src/example.py",
        "new_path": "src/example.py",
        "diff": "@@ -10,7 +10,7 @@\n class Calculator:\n     def add(self, a, b):\n-        return a + b\n+        return float(a) + float(b)"
    }


@pytest.fixture
def sample_glm_response():
    """Sample GLM API response for testing"""
    return {
        "choices": [
            {
                "message": {
                    "content": '{"comments": [{"file": "src/example.py", "line": 12, "comment": "Consider using type hints", "severity": "low"}]}'
                }
            }
        ],
        "usage": {
            "prompt_tokens": 1234,
            "completion_tokens": 567,
            "total_tokens": 1801
        }
    }


@pytest.fixture
def large_diff():
    """Large diff for testing chunking functionality"""
    lines = ["--- a/src/large_file.py", "+++ b/src/large_file.py", "@@ -1,50 +1,50 @@"]
    for i in range(50):
        lines.append(f"-def old_function_{i}():")
        lines.append(f"+def new_function_{i}():")
    return "\n".join(lines)


@pytest.fixture
def sample_analysis_result():
    """Sample analysis result for testing"""
    return {
        "comments": [
            {
                "file": "src/example.py",
                "line": 42,
                "comment": "Consider using list comprehension",
                "type": "suggestion",
                "severity": "low"
            },
            {
                "file": "src/example.py",
                "line": 58,
                "comment": "Potential security issue: user input not sanitized",
                "type": "security",
                "severity": "high"
            }
        ],
        "summary": "Found 2 issues: 1 suggestion, 1 security issue"
    }


class MockResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, json_data, status_code=200):
        self.json_data = json_data
        self.status_code = status_code
        self.text = str(json_data)
    
    def json(self):
        return self.json_data
    
    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")
        return None


@pytest.fixture
def mock_gitlab_response():
    """Mock GitLab API response"""
    return MockResponse([
        {
            "old_path": "src/example.py",
            "new_path": "src/example.py",
            "diff": "@@ -10,7 +10,7 @@\n class Calculator:\n     def add(self, a, b):\n-        return a + b\n+        return float(a) + float(b)"
        }
    ])


@pytest.fixture
def mock_glm_response():
    """Mock GLM API response"""
    return MockResponse({
        "choices": [
            {
                "message": {
                    "content": '{"comments": [{"file": "src/example.py", "line": 12, "comment": "Consider using type hints", "severity": "low"}]}'
                }
            }
        ]
    })