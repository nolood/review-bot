#!/usr/bin/env python3
"""
Test script to verify review bot components work correctly.
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

# Set test environment variables
os.environ.update({
    "CI": "true",
    "CI_PROJECT_ID": "123",
    "CI_MERGE_REQUEST_IID": "456",
    "GITLAB_TOKEN": "test_token",
    "GITLAB_API_URL": "https://gitlab.example.com/api/v4",
    "GLM_API_KEY": "test_glm_api_key",
    "GLM_API_URL": "https://api.example.com/v1/chat/completions"
})

def test_imports():
    """Test that all components can be imported."""
    # Test config imports
    from config.prompts import ReviewType
    
    from config.settings import Settings
    
    # Test utils imports
    from utils.exceptions import ReviewBotError, ConfigurationError
    
    from utils.logger import get_logger, setup_logging
    
    # Test core components
    from gitlab_client import GitLabClient
    
    from glm_client import GLMClient
    
    from diff_parser import DiffParser
    
    from comment_publisher import CommentPublisher

def test_review_type():
    """Test ReviewType enum."""
    from config.prompts import ReviewType
    
    assert ReviewType.GENERAL == "general"
    assert ReviewType.SECURITY == "security" 
    assert ReviewType.PERFORMANCE == "performance"

def test_logger():
    """Test logger functionality."""
    from utils.logger import get_logger, setup_logging
    
    setup_logging(level="INFO", format_type="text")
    logger = get_logger("test")
    
    logger.info("Test log message")

def test_settings():
    """Test settings with environment variables."""
    from config.settings import Settings
    
    settings = Settings.from_env()
    
    assert settings.gitlab_token == "test_token"
    assert settings.glm_api_key == "test_glm_api_key"
    assert settings.project_id == "123"
    assert settings.mr_iid == "456"

def main():
    """Run all tests."""
    print("🧪 Testing review bot components...")
    print()
    
    tests = [
        test_imports,
        test_review_type,
        test_logger,
        test_settings
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            test()
            print(f"✅ {test.__name__} passed")
            passed += 1
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
        print()
    
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Review bot components are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
