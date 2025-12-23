"""
Integration tests for refactored components.

These tests verify that the new modular components work correctly
and maintain the same functionality as the monolithic version.
"""

import pytest
from pathlib import Path


class TestRefactoredComponents:
    """Test cases for refactored components."""
    
    def test_module_structure(self):
        """Test that module structure is correct."""
        # Check that new modules exist
        src_path = Path(__file__).parent.parent / "src"
        expected_modules = [
            "cli_handler.py",
            "config_manager.py", 
            "review_processor.py",
            "diff_handler.py"
        ]
        
        for module in expected_modules:
            module_path = src_path / module
            assert module_path.exists(), f"Missing module: {module}"
    
    def test_class_sizes(self):
        """Test that refactored classes are within size limits."""
        src_path = Path(__file__).parent.parent / "src"
        
        # Check individual class files
        class_files = {
            "cli_handler.py": 300,      # CLI Handler should be <300 lines
            "config_manager.py": 300,   # Config Manager should be <300 lines
            "review_processor.py": 300,  # Review Processor should be <300 lines
            "diff_handler.py": 300       # Diff Handler should be <300 lines
        }
        
        for filename, max_lines in class_files.items():
            file_path = src_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    line_count = len(f.readlines())
                    assert line_count <= max_lines, \
                        f"{filename} has {line_count} lines, exceeds {max_lines} limit"
    
    def test_single_responsibility(self):
        """Test that each class has single responsibility."""
        src_path = Path(__file__).parent.parent / "src"
        
        # Check each module has focused purpose
        module_purposes = {
            "cli_handler.py": [
                "argparse", "CLI", "command-line", "parsing"
            ],
            "config_manager.py": [
                "configuration", "environment", "validation", "settings"
            ],
            "review_processor.py": [
                "process", "orchestrate", "workflow", "review"
            ],
            "diff_handler.py": [
                "diff", "chunk", "parse", "coordinate"
            ]
        }
        
        for filename, keywords in module_purposes.items():
            file_path = src_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read().lower()
                    
                # Check that content relates to expected purpose
                keyword_matches = sum(1 for kw in keywords if kw in content)
                assert keyword_matches >= len(keywords) // 2, \
                    f"{filename} doesn't seem focused on expected purpose"
    
    def test_type_hints(self):
        """Test that type hints are present."""
        src_path = Path(__file__).parent.parent / "src"
        refactored_files = [
            "cli_handler.py", "config_manager.py", 
            "review_processor.py", "diff_handler.py"
        ]
        
        for filename in refactored_files:
            file_path = src_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for type hints
                has_type_hints = (
                    'def ' in content and 
                    (': str' in content or ': int' in content or 
                     ': bool' in content or ': List[' in content or
                     ': Dict[' in content or ': Optional[' in content)
                )
                
                assert has_type_hints, \
                    f"{filename} should have type hints"
    
    def test_backward_compatibility(self):
        """Test that backward compatibility is maintained."""
        # Test that main entry point still works
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent))
            import review_bot
            
            # Check main function exists
            assert hasattr(review_bot, 'main')
            assert callable(review_bot.main)
            
            # Check ReviewType enum exists
            assert hasattr(review_bot, 'ReviewType')
            
            # Check process_merge_request function exists
            assert hasattr(review_bot, 'process_merge_request')
            
        except ImportError:
            pytest.skip("review_bot module not available")
    
    def test_component_interfaces(self):
        """Test that component interfaces are properly defined."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            
            from config.settings import SettingsProtocol
            
            # Check protocol methods are defined
            expected_methods = [
                'is_file_ignored', 'is_file_prioritized', 
                'get_gitlab_headers', 'get_glm_headers'
            ]
            
            for method in expected_methods:
                assert hasattr(SettingsProtocol, method), f"Protocol missing method: {method}"
                
        except ImportError:
            pytest.skip("SettingsProtocol not available")


class TestErrorHandling:
    """Test that error handling is maintained in refactored components."""
    
    def test_exception_imports(self):
        """Test that exceptions are properly imported."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            
            from utils.exceptions import (
                ReviewBotError, ConfigurationError, 
                DiffParsingError, CommentPublishError
            )
            
            # Test that exceptions are properly defined
            assert issubclass(ConfigurationError, ReviewBotError)
            assert issubclass(DiffParsingError, ReviewBotError)
            assert issubclass(CommentPublishError, ReviewBotError)
            
        except ImportError:
            pytest.skip("Exception modules not available")
    
    def test_logging_compatibility(self):
        """Test that logging is compatible."""
        try:
            import sys
            sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
            
            from utils.logger import get_logger, setup_logging
            
            # Test that logging functions are available
            logger = get_logger("test")
            assert logger is not None
            
            # Test that setup_logging can be called
            setup_logging(level="DEBUG", format_type="text")
            
        except ImportError:
            pytest.skip("Logger module not available")


class TestRefactoringQuality:
    """Test the quality of the refactoring work."""
    
    def test_file_line_counts(self):
        """Test that original file size is reduced."""
        # Check that original review_bot.py was reduced
        original_path = Path(__file__).parent.parent / "review_bot.py"
        if original_path.exists():
            with open(original_path, 'r') as f:
                original_lines = len(f.readlines())
            
            # Original should be less than before refactoring (was 1161 lines)
            assert original_lines < 1000, \
                f"Original file should be under 1000 lines, is {original_lines}"
    
    def test_dependency_injection_patterns(self):
        """Test that dependency injection patterns are used."""
        src_path = Path(__file__).parent.parent / "src"
        
        for filename in ["cli_handler.py", "config_manager.py", "review_processor.py"]:
            file_path = src_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read()
                
                # Check for dependency injection patterns
                has_di_patterns = (
                    'def __init__(self' in content and  # Constructor injection
                    'settings:' in content and      # Settings parameter
                    'self.settings' in content       # Stored dependency
                )
                
                assert has_di_patterns, \
                    f"{filename} should use dependency injection"
    
    def test_separation_of_concerns(self):
        """Test that concerns are properly separated."""
        src_path = Path(__file__).parent.parent / "src"
        
        # Each file should focus on its primary concern
        concern_keywords = {
            "cli_handler.py": {
                "primary": ["argparse", "cli", "command", "argument"],
                "should_not_have": ["process_merge_request", "analyze_code", "publish_comments"]
            },
            "config_manager.py": {
                "primary": ["validate", "environment", "settings", "configuration"],
                "should_not_have": ["argparse", "gitlab", "glm", "client"]
            },
            "review_processor.py": {
                "primary": ["process", "orchestrate", "workflow", "review"],
                "should_not_have": ["argparse", "environment", "validation"]
            },
            "diff_handler.py": {
                "primary": ["diff", "chunk", "parse", "coordinate"],
                "should_not_have": ["argparse", "publish", "analyze"]
            }
        }
        
        for filename, keywords in concern_keywords.items():
            file_path = src_path / filename
            if file_path.exists():
                with open(file_path, 'r') as f:
                    content = f.read().lower()
                
                # Check primary keywords
                primary_matches = sum(1 for kw in keywords["primary"] if kw in content)
                assert primary_matches >= len(keywords["primary"]) // 2, \
                    f"{filename} should focus on {keywords['primary']}"
                
                # Check for unwanted keywords
                unwanted_matches = sum(1 for kw in keywords["should_not_have"] if kw in content)
                assert unwanted_matches < len(keywords["should_not_have"]) // 2, \
                    f"{filename} should not contain {keywords['should_not_have']}"
        assert handler.logger == mock_logger
        
        # Validate args
        handler.validate_args(args)
        
        # Check review type parsing
        review_type = handler.parse_review_type(args.type)
        assert review_type == ReviewType.SECURITY
    
    @pytest.mark.skipif(not REFACTORED_AVAILABLE, reason="Refactored components not available")
    def test_config_environment_validation(self):
        """Test configuration manager environment validation."""
        mock_settings = Mock()
        mock_settings.glm_api_key = "test_key"
        mock_settings.gitlab_token = "test_token"
        mock_settings.project_id = "123"
        mock_settings.mr_iid = "456"
        mock_settings.glm_temperature = 0.3
        mock_settings.max_diff_size = 50000
        mock_settings.glm_api_url = "https://api.example.com"
        mock_settings.gitlab_api_url = "https://gitlab.example.com"
        mock_settings.ignore_file_patterns = ["*.min.js", "*.min.css"]
        mock_settings.prioritize_file_patterns = ["*.py", "*.js"]
        
        # Add required methods
        mock_settings.is_file_ignored = Mock(return_value=False)
        
        config_manager = ConfigurationManager(mock_settings)
        
        # Test dry run validation
        result = config_manager.validate_environment(dry_run=True)
        assert result is True
        
        # Test full validation
        result = config_manager.validate_environment(dry_run=False)
        assert result is True