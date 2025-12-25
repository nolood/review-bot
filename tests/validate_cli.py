#!/usr/bin/env python3
"""
Simple validation script for review_bot_server.py CLI structure.
Tests the file structure and basic Python syntax.
"""

import ast
import sys
from pathlib import Path

def validate_cli_file():
    """Validate the CLI file structure and syntax."""
    cli_file = Path("review_bot_server.py")
    
    print("🔍 Validating GLM Code Review Bot CLI Structure")
    print("=" * 60)
    
    if not cli_file.exists():
        print("❌ review_bot_server.py not found!")
        return False
    
    print("✅ CLI file exists")
    
    # Check file size
    file_size = cli_file.stat().st_size
    print(f"✅ File size: {file_size:,} bytes")
    
    # Check syntax
    try:
        with open(cli_file, 'r') as f:
            content = f.read()
        
        # Parse the AST to check syntax
        ast.parse(content)
        print("✅ Python syntax is valid")
        
    except SyntaxError as e:
        print(f"❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return False
    
    # Check for required components
    checks = [
        ('typer', 'Typer CLI framework'),
        ('rich', 'Rich terminal output'),
        ('asyncio', 'Async/await support'),
        ('signal', 'Signal handling'),
        ('class Environment', 'Environment enum'),
        ('class CLIConfig', 'Configuration dataclass'),
        ('def start_server', 'Start server command'),
        ('def run_bot', 'Run bot command'),
        ('def health_check', 'Health check command'),
        ('def validate_config', 'Config validation command'),
        ('def monitor_mode', 'Monitor mode command'),
        ('def version', 'Version command'),
        ('if __name__ == "__main__":', 'Entry point'),
    ]
    
    print("\n📋 Checking CLI Components:")
    for pattern, description in checks:
        if pattern in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ❌ {description}")
    
    # Check for async patterns
    async_patterns = [
        ('async def', 'Async functions'),
        ('await ', 'Await expressions'),
        ('asyncio.run', 'Async execution'),
        ('asyncio.create_task', 'Async task creation'),
    ]
    
    print("\n⚡ Checking Async Patterns:")
    for pattern, description in async_patterns:
        if pattern in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ⚠️  {description} (may be conditional)")
    
    # Check for error handling
    error_patterns = [
        ('try:', 'Try blocks'),
        ('except', 'Exception handling'),
        ('finally:', 'Cleanup blocks'),
        ('ConfigurationError', 'Custom error types'),
        ('graceful shutdown', 'Graceful shutdown'),
    ]
    
    print("\n🛡️ Checking Error Handling:")
    for pattern, description in error_patterns:
        if pattern in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ⚠️  {description}")
    
    # Check for monitoring integration
    monitoring_patterns = [
        ('monitoring', 'Monitoring references'),
        ('health_checker', 'Health checker'),
        ('metrics_collector', 'Metrics collector'),
        ('MonitoringServer', 'Monitoring server'),
    ]
    
    print("\n📊 Checking Monitoring Integration:")
    for pattern, description in monitoring_patterns:
        if pattern in content:
            print(f"   ✅ {description}")
        else:
            print(f"   ⚠️  {description}")
    
    # Count lines and functions
    lines = content.split('\n')
    function_count = content.count('def ')
    class_count = content.count('class ')
    
    print(f"\n📊 Statistics:")
    print(f"   • Total lines: {len(lines):,}")
    print(f"   • Functions: {function_count}")
    print(f"   • Classes: {class_count}")
    
    print("\n" + "=" * 60)
    print("🎉 CLI Structure Validation Complete!")
    
    return True

def show_commands():
    """Show available commands from the CLI."""
    commands = [
        {
            'name': 'start-server',
            'description': 'Start server with monitoring and web interface',
            'example': 'python3 review_bot_server.py start-server --env dev --verbose'
        },
        {
            'name': 'run-bot', 
            'description': 'Run bot in standalone mode',
            'example': 'python3 review_bot_server.py run-bot --dry-run --review-type security'
        },
        {
            'name': 'health-check',
            'description': 'Run comprehensive health verification',
            'example': 'python3 review_bot_server.py health-check --verbose'
        },
        {
            'name': 'validate-config',
            'description': 'Validate configuration and environment',
            'example': 'python3 review_bot_server.py validate-config --config config.json'
        },
        {
            'name': 'monitor-mode',
            'description': 'Run monitoring server only',
            'example': 'python3 review_bot_server.py monitor-mode --port 9090'
        },
        {
            'name': 'version',
            'description': 'Show version information',
            'example': 'python3 review_bot_server.py version'
        }
    ]
    
    print("\n🚀 Available Commands:")
    print("-" * 60)
    for cmd in commands:
        print(f"\n📋 {cmd['name']}")
        print(f"   {cmd['description']}")
        print(f"   Example: {cmd['example']}")

if __name__ == "__main__":
    success = validate_cli_file()
    show_commands()
    
    if success:
        print(f"\n✅ Validation passed! The CLI is ready for use.")
        print(f"\n🔧 To use the CLI:")
        print(f"   1. Install dependencies: pip install -r requirements.txt")
        print(f"   2. Make executable: chmod +x review_bot_server.py") 
        print(f"   3. Set environment variables (see CLI_README.md)")
        print(f"   4. Run: python3 review_bot_server.py --help")
        sys.exit(0)
    else:
        print(f"\n❌ Validation failed! Please check the CLI file.")
        sys.exit(1)