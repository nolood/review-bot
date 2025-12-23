"""
Tests for CLI Handler component.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from argparse import Namespace

from src.cli_handler import CLIHandler
from src.config.prompts import ReviewType
from src.utils.exceptions import ConfigurationError


class TestCLIHandler:
    """Test cases for CLI Handler."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.mock_settings = Mock()
        self.mock_settings.log_level = "INFO"
        self.mock_settings.log_format = "text"
        self.mock_settings.log_file = None
        self.cli_handler = CLIHandler(self.mock_settings)
    
    def test_create_parser(self):
        """Test argument parser creation."""
        parser = self.cli_handler.create_parser()
        
        # Test basic parsing
        args = parser.parse_args([])
        assert args.type == "general"
        assert args.dry_run is False
        assert args.custom_prompt is None
        assert args.max_chunks is None
        
        # Test with arguments
        args = parser.parse_args(["--type", "security", "--dry-run"])
        assert args.type == "security"
        assert args.dry_run is True
    
    def test_parse_review_type(self):
        """Test review type parsing."""
        # Valid types
        assert self.cli_handler.parse_review_type("general") == ReviewType.GENERAL
        assert self.cli_handler.parse_review_type("security") == ReviewType.SECURITY
        assert self.cli_handler.parse_review_type("performance") == ReviewType.PERFORMANCE
        
        # Invalid type
        with pytest.raises(ValueError):
            self.cli_handler.parse_review_type("invalid")
    
    @patch('src.cli_handler.setup_logging')
    @patch('src.cli_handler.get_logger')
    def test_setup_logging_success(self, mock_get_logger, mock_setup_logging):
        """Test successful logging setup."""
        mock_logger = Mock()
        mock_get_logger.return_value = mock_logger
        mock_setup_logging.return_value = None
        
        args = Namespace(log_level="DEBUG", log_format="json", log_file="/tmp/test.log")
        
        result = self.cli_handler.setup_logging(args)
        
        assert result is True
        mock_setup_logging.assert_called_once_with(
            level="DEBUG",
            format_type="json",
            log_file="/tmp/test.log"
        )
        mock_get_logger.assert_called_once_with("cli")
        assert self.cli_handler.logger == mock_logger
    
    @patch('src.cli_handler.setup_logging')
    def test_setup_logging_failure(self, mock_setup_logging):
        """Test logging setup failure."""
        mock_setup_logging.side_effect = Exception("Setup failed")
        
        args = Namespace(log_level="DEBUG", log_format="json", log_file=None)
        
        result = self.cli_handler.setup_logging(args)
        
        assert result is False
    
    def test_validate_args_success(self):
        """Test argument validation success."""
        # Valid arguments
        args = Namespace(
            max_chunks=5,
            custom_prompt="Focus on security"
        )
        
        # Should not raise exception
        self.cli_handler.validate_args(args)
    
    def test_validate_args_invalid_max_chunks(self):
        """Test argument validation with invalid max_chunks."""
        args = Namespace(max_chunks=0, custom_prompt=None)
        
        with pytest.raises(ConfigurationError, match="max-chunks must be a positive integer"):
            self.cli_handler.validate_args(args)
    
    def test_validate_args_empty_custom_prompt(self):
        """Test argument validation with empty custom prompt."""
        args = Namespace(max_chunks=None, custom_prompt="   ")
        
        with pytest.raises(ConfigurationError, match="custom-prompt cannot be empty"):
            self.cli_handler.validate_args(args)
    
    @patch('builtins.print')
    def test_print_success_summary(self, mock_print):
        """Test success summary printing."""
        result = {
            "processing_time": 2.5,
            "stats": {
                "total_comments_generated": 10,
                "file_comments_published": 5,
                "inline_comments_published": 3
            }
        }
        
        self.cli_handler.print_success_summary(result, dry_run=False)
        
        # Verify print calls
        mock_print.assert_any_call("✅ Review completed in 2.50s")
        mock_print.assert_any_call("📝 Generated 10 comments")
        mock_print.assert_any_call("📤 Published 8 comments")
    
    @patch('builtins.print')
    def test_print_success_summary_dry_run(self, mock_print):
        """Test success summary printing in dry run mode."""
        result = {
            "processing_time": 2.5,
            "stats": {
                "total_comments_generated": 10,
                "file_comments_published": 5,
                "inline_comments_published": 3
            }
        }
        
        self.cli_handler.print_success_summary(result, dry_run=True)
        
        # Verify print calls - should not show published count in dry run
        mock_print.assert_any_call("✅ Review completed in 2.50s")
        mock_print.assert_any_call("📝 Generated 10 comments")
        # Should not call the publish print
        for call in mock_print.call_args_list:
            if "Published" in str(call):
                pytest.fail("Should not show published count in dry run")
    
    def test_parse_args(self):
        """Test argument parsing."""
        parser = self.cli_handler.create_parser()
        
        # Mock sys.argv
        test_args = ["--type", "security", "--max-chunks", "3"]
        
        args = self.cli_handler.parse_args(test_args)
        
        assert args.type == "security"
        assert args.max_chunks == 3
        assert args.dry_run is False