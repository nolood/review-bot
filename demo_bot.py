#!/usr/bin/env python3
"""
Demo script to show review bot functionality
"""

import os
import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

def demo_review_bot():
    """Demonstrate review bot functionality with environment validation."""
    print("🚀 GLM Code Review Bot Demo")
    print("=" * 50)
    
    # Set minimal environment for demo
    os.environ["GITLAB_TOKEN"] = "demo_token"
    os.environ["GLM_API_KEY"] = "demo_api_key"
    os.environ["CI_PROJECT_ID"] = "123"
    os.environ["CI_MERGE_REQUEST_IID"] = "456"
    
    try:
        # Test core imports
        print("📦 Testing imports...")
        from config.prompts import ReviewType
        from config.settings import Settings
        from utils.logger import setup_logging, get_logger
        from utils.exceptions import ReviewBotError, ConfigurationError
        
        print("✅ All core imports successful")
        
        # Test settings
        print("\n⚙️ Testing settings...")
        settings = Settings.from_env()
        print(f"✅ Settings loaded: project_id={settings.project_id}, mr_iid={settings.mr_iid}")
        
        # Test logging
        print("\n📝 Testing logging...")
        setup_logging(level="INFO", format_type="text")
        logger = get_logger("demo")
        logger.info("Demo log message")
        print("✅ Logging working")
        
        # Test review types
        print("\n🔍 Testing review types...")
        print(f"✅ Available review types: {[rt.value for rt in ReviewType]}")
        
        # Test validation
        print("\n🔧 Testing validation...")
        from review_bot import validate_environment
        validate_environment(dry_run=True)
        print("✅ Environment validation passed")
        
        print("\n🎉 Demo completed successfully!")
        print("\nTo use with real GitLab/GLM:")
        print("1. Set your actual environment variables:")
        print("   export GITLAB_TOKEN=your_token")
        print("   export GLM_API_KEY=your_key") 
        print("   export CI_PROJECT_ID=your_project_id")
        print("   export CI_MERGE_REQUEST_IID=your_mr_id")
        print("\n2. Run the bot:")
        print("   python3 review_bot.py")
        print("\n3. For options:")
        print("   python3 review_bot.py --help")
        
        return True
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        return False

if __name__ == "__main__":
    success = demo_review_bot()
    sys.exit(0 if success else 1)