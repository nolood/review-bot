"""
Simple test to verify the test setup works
"""
import os


def test_environment_variables():
    """Test that required environment variables are set for testing"""
    assert os.getenv("CI") == "true"
    assert os.getenv("CI_PROJECT_ID") == "123"
    assert os.getenv("CI_MERGE_REQUEST_IID") == "456"


def test_simple_math():
    """A simple test to verify pytest works"""
    assert 1 + 1 == 2


def test_string_operations():
    """Test string operations"""
    text = "Hello, World!"
    assert text.startswith("Hello")
    assert text.endswith("World!")
    assert "World" in text