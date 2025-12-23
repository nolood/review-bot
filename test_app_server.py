#!/usr/bin/env python3
"""
Test script for application server.

This script tests basic functionality of app server
to ensure it can be imported and instantiated correctly.
"""

import asyncio
import os
import sys
import traceback

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_import():
    """Test that app server can be imported."""
    try:
        from app_server import AppServer, ServerConfig
        print("✅ AppServer imported successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to import AppServer: {e}")
        traceback.print_exc()
        return False

def test_server_creation():
    """Test that server can be created."""
    try:
        from app_server import AppServer, ServerConfig
        
        config = ServerConfig(
            host="127.0.0.1",
            port=8001,
            log_level="info"
        )
        
        server = AppServer(config=config)
        print("✅ AppServer created successfully")
        print(f"   - Host: {server.config.host}")
        print(f"   - Port: {server.config.port}")
        print(f"   - FastAPI available: {server.app is not None}")
        return True
    except Exception as e:
        print(f"❌ Failed to create AppServer: {e}")
        traceback.print_exc()
        return False

def test_settings_integration():
    """Test settings integration."""
    try:
        from app_server import create_server_from_settings
        
        server = create_server_from_settings()
        print("✅ Server created from settings successfully")
        print(f"   - Settings loaded: {server.settings is not None}")
        return True
    except Exception as e:
        print(f"❌ Failed to create server from settings: {e}")
        traceback.print_exc()
        return False

def test_fastapi_endpoints():
    """Test FastAPI endpoint creation."""
    try:
        from app_server import AppServer, ServerConfig
        
        config = ServerConfig(enable_monitoring=False)  # Disable monitoring for simple test
        server = AppServer(config=config)
        
        if server.app:
            # Check if endpoints were created
            routes = [route.path for route in server.app.routes]
            expected_endpoints = ['/health', '/api/v1/status', '/']
            
            for endpoint in expected_endpoints:
                if endpoint in routes:
                    print(f"✅ Endpoint {endpoint} found")
                else:
                    print(f"❌ Endpoint {endpoint} missing")
                    return False
            
            print("✅ All expected endpoints found")
            return True
        else:
            print("ℹ️  FastAPI not available, skipping endpoint test")
            return True
            
    except Exception as e:
        print(f"❌ Failed to test endpoints: {e}")
        traceback.print_exc()
        return False

async def test_background_processing():
    """Test background task processing setup."""
    try:
        from app_server import AppServer, ServerConfig, ReviewTask, TaskStatus
        
        config = ServerConfig(enable_monitoring=False)
        server = AppServer(config=config)
        
        # Create a test task
        import uuid
        from datetime import datetime
        
        task = ReviewTask(
            task_id=str(uuid.uuid4()),
            project_id="123",
            mr_iid="456",
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow()
        )
        
        server.active_tasks[task.task_id] = task
        
        # Test task management
        assert task.task_id in server.active_tasks
        assert len(server.active_tasks) == 1
        
        print("✅ Background task processing setup works")
        return True
        
    except Exception as e:
        print(f"❌ Failed to test background processing: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("🚀 Testing GLM Code Review Bot Application Server")
    print("=" * 50)
    
    tests = [
        ("Import Test", test_import),
        ("Server Creation Test", test_server_creation),
        ("Settings Integration Test", test_settings_integration),
        ("FastAPI Endpoints Test", test_fastapi_endpoints),
        ("Background Processing Test", lambda: asyncio.run(test_background_processing())),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 {test_name}:")
        try:
            if test_func():
                passed += 1
            else:
                print("   Test failed!")
        except Exception as e:
            print(f"   Test error: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())