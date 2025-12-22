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

def test_imports():
    """Test that all components can be imported."""
    print("Testing imports...")
    
    try:
        # Test config imports
        from config.prompts import ReviewType
        print("✅ ReviewType imported successfully")
        
        from config.settings import Settings
        print("✅ Settings imported successfully")
        
        # Test utils imports
        from utils.exceptions import ReviewBotError, ConfigurationError
        print("✅ Exceptions imported successfully")
        
        from utils.logger import get_logger, setup_logging
        print("✅ Logger imported successfully")
        
        # Test core components
        from gitlab_client import GitLabClient
        print("✅ GitLabClient imported successfully")
        
        from glm_client import GLMClient
        print("✅ GLMClient imported successfully")
        
        from diff_parser import DiffParser
        print("✅ DiffParser imported successfully")
        
        from comment_publisher import CommentPublisher
        print("✅ CommentPublisher imported successfully")
        
        return True
        
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_review_type():
    """Test ReviewType enum."""
    try:
        from config.prompts import ReviewType
        
        assert ReviewType.GENERAL == "general"
        assert ReviewType.SECURITY == "security" 
        assert ReviewType.PERFORMANCE == "performance"
        
        print("✅ ReviewType enum working correctly")
        return True
    except Exception as e:
        print(f"❌ ReviewType test failed: {e}")
        return False

def test_logger():
    """Test logger functionality."""
    try:
        from utils.logger import get_logger, setup_logging
        
        setup_logging(level="INFO", format_type="text")
        logger = get_logger("test")
        
        logger.info("Test log message")
        print("✅ Logger working correctly")
        return True
    except Exception as e:
        print(f"❌ Logger test failed: {e}")
        return False

def test_settings():
    """Test settings with environment variables."""
    try:
        # Set minimal environment variables for testing
        os.environ["GITLAB_TOKEN"] = "test_token"
        os.environ["GLM_API_KEY"] = "test_key" 
        os.environ["CI_PROJECT_ID"] = "123"
        os.environ["CI_MERGE_REQUEST_IID"] = "456"
        
        from config.settings import Settings
        
        settings = Settings.from_env()
        
        assert settings.gitlab_token == "test_token"
        assert settings.glm_api_key == "test_key"
        assert settings.project_id == "123"
        assert settings.mr_iid == "456"
        
        print("✅ Settings working correctly")
        return True
    except Exception as e:
        print(f"❌ Settings test failed: {e}")
        return False

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
        if test():
            passed += 1
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