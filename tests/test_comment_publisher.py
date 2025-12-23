"""
Unit tests for Comment Publisher module
Tests comment formatting, publishing, and error handling
"""
import json
import time
import pytest
from unittest.mock import Mock, patch, MagicMock, call
from datetime import datetime

from src.comment_publisher import (
    CommentPublisher,
    CommentType,
    SeverityLevel,
    FormattedComment,
    CommentBatch
)
from src.utils.exceptions import CommentPublishError
from src.gitlab_client import GitLabClient


# Module-level fixtures for shared use
@pytest.fixture
def mock_gitlab_client():
    """Mock GitLab client"""
    return Mock(spec=GitLabClient)


@pytest.fixture
def mock_settings():
    """Mock settings with api_request_delay"""
    settings_mock = Mock()
    settings_mock.api_request_delay = 1.0
    return settings_mock


class TestCommentTypeAndSeverity:
    """Test enums and basic data structures"""

    def test_comment_type_values(self):
        """Test CommentType enum values"""
        assert CommentType.ISSUE.value == "issue"
        assert CommentType.SUGGESTION.value == "suggestion"
        assert CommentType.PRAISE.value == "praise"
        assert CommentType.QUESTION.value == "question"
        assert CommentType.SUMMARY.value == "summary"

    def test_severity_level_values(self):
        """Test SeverityLevel enum values"""
        assert SeverityLevel.LOW.value == "low"
        assert SeverityLevel.MEDIUM.value == "medium"
        assert SeverityLevel.HIGH.value == "high"
        assert SeverityLevel.CRITICAL.value == "critical"

    def test_formatted_comment_creation(self):
        """Test FormattedComment dataclass creation"""
        comment = FormattedComment(
            comment_type=CommentType.SUGGESTION,
            severity=SeverityLevel.MEDIUM,
            file_path="src/example.py",
            line_number=42,
            title="Test comment",
            body="This is a test comment"
        )
        
        assert comment.comment_type == CommentType.SUGGESTION
        assert comment.severity == SeverityLevel.MEDIUM
        assert comment.file_path == "src/example.py"
        assert comment.line_number == 42
        assert comment.title == "Test comment"
        assert comment.body == "This is a test comment"
        assert comment.suggestion is None
        assert comment.code_snippet is None
        assert comment.metadata == {}

    def test_comment_batch_creation(self):
        """Test CommentBatch dataclass creation"""
        batch = CommentBatch(
            summary_comment="Test summary",
            file_comments=[Mock(spec=FormattedComment)],
            inline_comments=[Mock(spec=FormattedComment)]
        )
        
        assert batch.summary_comment == "Test summary"
        assert len(batch.file_comments) == 1
        assert len(batch.inline_comments) == 1


class TestCommentPublisherInit:
    """Test CommentPublisher initialization"""

    def test_init_with_custom_client(self, mock_gitlab_client, mock_settings):
        """Test initialization with custom GitLab client"""
        with patch('src.comment_publisher.settings', mock_settings):
            publisher = CommentPublisher(gitlab_client=mock_gitlab_client)
            
            assert publisher.gitlab_client == mock_gitlab_client
            assert publisher.comment_delay == 1.0
            assert publisher.max_batch_size == 10
            assert publisher.last_comment_time == 0.0

    def test_init_without_client(self, mock_settings):
        """Test initialization without GitLab client (creates new one)"""
        with patch('src.comment_publisher.GitLabClient') as mock_client_class, \
             patch('src.comment_publisher.settings', mock_settings):
            
            mock_client_instance = Mock(spec=GitLabClient)
            mock_client_class.return_value = mock_client_instance
            
            publisher = CommentPublisher()
            
            mock_client_class.assert_called_once()
            assert publisher.gitlab_client == mock_client_instance

    def test_init_with_none_settings(self):
        """Test initialization when settings is None"""
        with patch('src.comment_publisher.settings', None), \
             patch('src.comment_publisher.GitLabClient') as mock_client_class:
            
            mock_client_instance = Mock(spec=GitLabClient)
            mock_client_class.return_value = mock_client_instance
            
            publisher = CommentPublisher()
            
            # Should handle None settings gracefully
            assert publisher.gitlab_client == mock_client_instance


class TestFormatComments:
    """Test comment formatting from GLM responses"""

    @pytest.fixture
    def publisher(self, mock_gitlab_client, mock_settings):
        """Create CommentPublisher instance for testing"""
        with patch('src.comment_publisher.settings', mock_settings):
            return CommentPublisher(gitlab_client=mock_gitlab_client)

    @pytest.fixture
    def sample_glm_dict_response(self):
        """Sample GLM response as dictionary"""
        return {
            "comments": [
                {
                    "file": "src/example.py",
                    "line": 42,
                    "comment": "Consider using type hints",
                    "type": "suggestion",
                    "severity": "low"
                }
            ]
        }

    @pytest.fixture
    def sample_glm_string_response(self, sample_glm_dict_response):
        """Sample GLM response as JSON string"""
        return json.dumps(sample_glm_dict_response)

    def test_format_comments_with_dict(self, publisher, sample_glm_dict_response):
        """Test formatting comments from dictionary response"""
        result = publisher.format_comments(sample_glm_dict_response)
        
        assert isinstance(result, CommentBatch)
        assert len(result.file_comments) == 0  # No file comments without line numbers
        assert len(result.inline_comments) == 1  # Has line number, so it's inline
        assert result.summary_comment is None
        
        comment = result.inline_comments[0]
        assert comment.comment_type == CommentType.SUGGESTION
        assert comment.severity == SeverityLevel.LOW
        assert comment.file_path == "src/example.py"
        assert comment.line_number == 42

    def test_format_comments_with_string(self, publisher, sample_glm_string_response):
        """Test formatting comments from JSON string response"""
        result = publisher.format_comments(sample_glm_string_response)
        
        assert isinstance(result, CommentBatch)
        assert len(result.inline_comments) == 1
        assert result.inline_comments[0].file_path == "src/example.py"

    def test_format_comments_different_structures(self, publisher):
        """Test formatting comments with different response structures"""
        # Test with "feedback" key
        response1 = {"feedback": [{"comment": "Test", "type": "issue"}]}
        result1 = publisher.format_comments(response1)
        assert len(result1.file_comments) == 1
        
        # Test with "analysis" key
        response2 = {"analysis": [{"comment": "Test", "type": "suggestion"}]}
        result2 = publisher.format_comments(response2)
        assert len(result2.file_comments) == 1
        
        # Test with direct list
        response3 = [{"comment": "Test", "type": "praise"}]
        result3 = publisher.format_comments(response3)
        assert len(result3.file_comments) == 1
        
        # Test with single object
        response4 = {"comment": "Test", "type": "question"}
        result4 = publisher.format_comments(response4)
        assert len(result4.file_comments) == 1

    def test_format_comments_summary_type(self, publisher):
        """Test formatting summary comments"""
        response = {
            "comments": [
                {
                    "type": "summary",
                    "comment": "Overall code looks good"
                },
                {
                    "file": "src/test.py",
                    "comment": "Minor issue here",
                    "type": "issue"
                }
            ]
        }
        
        result = publisher.format_comments(response)
        
        assert result.summary_comment == "Overall code looks good"
        assert len(result.file_comments) == 1

    def test_format_comments_invalid_json(self, publisher):
        """Test error handling for invalid JSON"""
        with pytest.raises(CommentPublishError, match="Invalid GLM response format"):
            publisher.format_comments("invalid json string")

    def test_format_comments_missing_keys(self, publisher):
        """Test formatting with missing optional keys"""
        response = {
            "comments": [
                {
                    # Missing type, should default to suggestion
                    "comment": "Test comment",
                    # Missing severity, should default to low
                    "file": "src/test.py"
                }
            ]
        }
        
        result = publisher.format_comments(response)
        
        comment = result.file_comments[0]
        assert comment.comment_type == CommentType.SUGGESTION  # Default
        assert comment.severity == SeverityLevel.LOW  # Default

    def test_format_comments_line_number_string(self, publisher):
        """Test line number as string gets converted to int"""
        response = {
            "comments": [
                {
                    "file": "src/test.py",
                    "line": "42",  # String instead of int
                    "comment": "Test comment"
                }
            ]
        }
        
        result = publisher.format_comments(response)
        
        comment = result.inline_comments[0]  # Has line number, so it's inline
        assert comment.line_number == 42
        assert isinstance(comment.line_number, int)

    def test_format_comments_invalid_line_number(self, publisher):
        """Test invalid line number string"""
        response = {
            "comments": [
                {
                    "file": "src/test.py",
                    "line": "invalid",  # Invalid string
                    "comment": "Test comment"
                }
            ]
        }
        
        result = publisher.format_comments(response)
        
        comment = result.file_comments[0]
        assert comment.line_number is None

    def test_extract_comments_from_response(self, publisher):
        """Test the private _extract_comments_from_response method"""
        # Test with comments key
        response1 = {"comments": [{"id": 1}, {"id": 2}]}
        comments1 = publisher._extract_comments_from_response(response1)
        assert len(comments1) == 2
        
        # Test with feedback key
        response2 = {"feedback": [{"id": 1}]}
        comments2 = publisher._extract_comments_from_response(response2)
        assert len(comments2) == 1
        
        # Test with analysis key
        response3 = {"analysis": [{"id": 1}]}
        comments3 = publisher._extract_comments_from_response(response3)
        assert len(comments3) == 1
        
        # Test with direct list
        response4 = [{"id": 1}, {"id": 2}]
        comments4 = publisher._extract_comments_from_response(response4)
        assert len(comments4) == 2
        
        # Test with single object
        response5 = {"id": 1}
        comments5 = publisher._extract_comments_from_response(response5)
        assert len(comments5) == 1

    def test_parse_comment_data(self, publisher):
        """Test the private _parse_comment_data method"""
        comment_data = {
            "type": "issue",
            "severity": "high",
            "file": "src/test.py",
            "line": 42,
            "title": "Test Title",
            "comment": "Test comment body",
            "suggestion": "Fix this",
            "code": "example code",
            "metadata": {"key": "value"}
        }
        
        result = publisher._parse_comment_data(comment_data)
        
        assert result.comment_type == CommentType.ISSUE
        assert result.severity == SeverityLevel.HIGH
        assert result.file_path == "src/test.py"
        assert result.line_number == 42
        assert result.title == "Test Title"
        assert result.body == "Test comment body"
        assert result.suggestion == "Fix this"
        assert result.code_snippet == "example code"
        assert result.metadata == {"key": "value"}

    def test_parse_comment_data_alternative_keys(self, publisher):
        """Test parsing with alternative key names"""
        comment_data = {
            "category": "suggestion",  # Alternative to "type"
            "priority": "medium",      # Alternative to "severity"
            "path": "src/test.py",    # Alternative to "file"
            "line_number": 42,        # Alternative to "line"
            "subject": "Test Title",  # Alternative to "title"
            "description": "Test comment body",  # Alternative to "comment"
            "snippet": "example code"  # Alternative to "code"
        }
        
        result = publisher._parse_comment_data(comment_data)
        
        assert result.comment_type == CommentType.SUGGESTION
        assert result.severity == SeverityLevel.MEDIUM
        assert result.file_path == "src/test.py"
        assert result.line_number == 42
        assert result.title == "Test Title"
        assert result.body == "Test comment body"
        assert result.code_snippet == "example code"

    def test_group_and_format_comments(self, publisher):
        """Test the private _group_and_format_comments method"""
        comments = [
            {
                "type": "summary",
                "comment": "Overall summary"
            },
            {
                "file": "src/test.py",
                "line": 42,
                "comment": "Inline comment"
            },
            {
                "file": "src/test.py",
                "comment": "File comment"
            }
        ]
        
        result = publisher._group_and_format_comments(comments)
        
        assert result.summary_comment == "Overall summary"
        assert len(result.inline_comments) == 1
        assert len(result.file_comments) == 1
        assert result.inline_comments[0].line_number == 42
        assert result.file_comments[0].line_number is None


class TestCommentFormatting:
    """Test markdown formatting of comments"""

    @pytest.fixture
    def publisher(self, mock_gitlab_client, mock_settings):
        """Create CommentPublisher instance for testing"""
        with patch('src.comment_publisher.settings', mock_settings):
            return CommentPublisher(gitlab_client=mock_gitlab_client)

    def test_format_summary_comment(self, publisher):
        """Test summary comment formatting"""
        summary = "Code looks good overall"
        result = publisher._format_summary_comment(summary)
        
        assert "🤖 Code Review Summary" in result
        assert summary in result
        assert "Generated by GLM Code Review Bot" in result
        assert "UTC" in result

    def test_format_summary_comment_with_mr_details(self, publisher):
        """Test summary formatting with MR details"""
        summary = "Test summary"
        mr_details = {"title": "Test MR", "author": "test_user"}
        
        result = publisher._format_summary_comment(summary, mr_details)
        
        assert summary in result
        # MR details aren't currently used in formatting but should not cause errors

    def test_format_file_comment_basic(self, publisher):
        """Test basic file comment formatting"""
        comment = FormattedComment(
            comment_type=CommentType.SUGGESTION,
            severity=SeverityLevel.LOW,
            title="Test Issue",
            body="This is a test comment"
        )
        
        result = publisher._format_file_comment(comment)
        
        assert "💡" in result  # Severity emoji
        assert "💭" in result  # Type emoji
        assert "**Test Issue**" in result
        assert "This is a test comment" in result
        assert "`LOW`" in result  # Severity badge

    def test_format_file_comment_with_code(self, publisher):
        """Test file comment with code snippet"""
        comment = FormattedComment(
            comment_type=CommentType.ISSUE,
            severity=SeverityLevel.HIGH,
            title="Code Issue",
            body="Problem in code",
            code_snippet="def bad_function():\n    pass"
        )
        
        result = publisher._format_file_comment(comment)
        
        assert "🔴" in result  # Severity emoji
        assert "🐛" in result  # Type emoji
        assert "```" in result
        assert "def bad_function():" in result

    def test_format_file_comment_with_suggestion(self, publisher):
        """Test file comment with suggestion"""
        comment = FormattedComment(
            comment_type=CommentType.SUGGESTION,
            severity=SeverityLevel.MEDIUM,
            title="Improvement",
            body="Could be better",
            suggestion="Use list comprehension"
        )
        
        result = publisher._format_file_comment(comment)
        
        assert "⚠️" in result  # Severity emoji
        assert "**Suggestion:** Use list comprehension" in result

    def test_format_file_comment_with_file_info(self, publisher):
        """Test file comment with file path and line number"""
        comment = FormattedComment(
            comment_type=CommentType.QUESTION,
            severity=SeverityLevel.LOW,
            title="Question",
            body="Why this approach?",
            file_path="src/example.py",
            line_number=42
        )
        
        result = publisher._format_file_comment(comment)
        
        assert "📁 `src/example.py`:42" in result

    def test_format_file_comment_all_features(self, publisher):
        """Test file comment with all features"""
        comment = FormattedComment(
            comment_type=CommentType.ISSUE,
            severity=SeverityLevel.CRITICAL,
            title="Critical Issue",
            body="Security vulnerability",
            suggestion="Fix immediately",
            code_snippet="eval(user_input)",
            file_path="src/unsafe.py",
            line_number=100
        )
        
        result = publisher._format_file_comment(comment)
        
        assert "🚨" in result  # Severity emoji
        assert "🐛" in result  # Type emoji
        assert "`CRITICAL`" in result
        assert "```" in result
        assert "**Suggestion:**" in result
        assert "📁 `src/unsafe.py`:100" in result

    def test_group_comments_by_file(self, publisher):
        """Test grouping comments by file"""
        comments = [
            FormattedComment(
                comment_type=CommentType.SUGGESTION,
                severity=SeverityLevel.LOW,
                file_path="src/file1.py"
            ),
            FormattedComment(
                comment_type=CommentType.ISSUE,
                severity=SeverityLevel.HIGH,
                file_path="src/file2.py"
            ),
            FormattedComment(
                comment_type=CommentType.QUESTION,
                severity=SeverityLevel.LOW,
                file_path="src/file1.py"
            ),
            FormattedComment(
                comment_type=CommentType.PRAISE,
                severity=SeverityLevel.LOW,
                file_path=None  # Should be grouped as "general"
            )
        ]
        
        result = publisher._group_comments_by_file(comments)
        
        assert len(result) == 3  # file1.py, file2.py, general
        assert len(result["src/file1.py"]) == 2
        assert len(result["src/file2.py"]) == 1
        assert len(result["general"]) == 1


class TestPublishingMethods:
    """Test comment publishing methods"""

    @pytest.fixture
    def publisher(self, mock_gitlab_client, mock_settings):
        """Create CommentPublisher instance for testing"""
        with patch('src.comment_publisher.settings', mock_settings):
            return CommentPublisher(gitlab_client=mock_gitlab_client)

    @pytest.fixture
    def mr_details(self):
        """Sample MR details for testing"""
        return {
            "id": 456,
            "title": "Test MR",
            "diff_refs": {
                "base_sha": "abc123",
                "start_sha": "def456",
                "head_sha": "ghi789"
            }
        }

    def test_publish_review_summary_success(self, publisher, mr_details):
        """Test successful summary publishing"""
        # Mock GitLab client response
        mock_response = {"id": 123, "body": "Test comment"}
        publisher.gitlab_client.post_comment.return_value = mock_response
        
        summary = "Code review completed"
        result = publisher.publish_review_summary(summary, mr_details)
        
        assert result == mock_response
        publisher.gitlab_client.post_comment.assert_called_once()
        
        # Check the formatted comment was passed
        call_args = publisher.gitlab_client.post_comment.call_args[0][0]
        assert "Code review completed" in call_args
        assert "🤖 Code Review Summary" in call_args

    def test_publish_review_summary_without_mr_details(self, publisher):
        """Test summary publishing without MR details"""
        mock_response = {"id": 123}
        publisher.gitlab_client.post_comment.return_value = mock_response
        
        summary = "Simple summary"
        result = publisher.publish_review_summary(summary)
        
        assert result == mock_response
        publisher.gitlab_client.post_comment.assert_called_once()

    def test_publish_review_summary_api_error(self, publisher):
        """Test summary publishing with API error"""
        publisher.gitlab_client.post_comment.side_effect = Exception("API Error")
        
        with pytest.raises(CommentPublishError, match="Summary publishing failed"):
            publisher.publish_review_summary("Test summary")

    def test_publish_file_comments_empty(self, publisher):
        """Test publishing empty file comments list"""
        result = publisher.publish_file_comments([])
        assert result == []

    def test_publish_file_comments_success(self, publisher, mr_details):
        """Test successful file comments publishing"""
        # Mock responses
        mock_response1 = {"id": 1}
        mock_response2 = {"id": 2}
        publisher.gitlab_client.post_comment.return_value = mock_response1
        publisher.gitlab_client.post_inline_comment.return_value = mock_response2
        
        comments = [
            FormattedComment(
                comment_type=CommentType.SUGGESTION,
                severity=SeverityLevel.LOW,
                file_path="src/file1.py",
                body="General comment"
            ),
            FormattedComment(
                comment_type=CommentType.ISSUE,
                severity=SeverityLevel.HIGH,
                file_path="src/file2.py",
                line_number=42,
                body="Inline comment"
            )
        ]
        
        result = publisher.publish_file_comments(comments, mr_details)
        
        assert len(result) == 2
        assert result[0] == mock_response1
        assert result[1] == mock_response2
        
        # Verify correct methods were called
        publisher.gitlab_client.post_comment.assert_called_once()
        publisher.gitlab_client.post_inline_comment.assert_called_once()

    def test_publish_file_comments_api_error(self, publisher, mr_details):
        """Test file comments publishing with API error"""
        publisher.gitlab_client.post_comment.side_effect = Exception("API Error")
        
        comments = [
            FormattedComment(
                comment_type=CommentType.SUGGESTION,
                severity=SeverityLevel.LOW,
                file_path="src/file1.py",
                body="Test comment"
            )
        ]
        
        with pytest.raises(CommentPublishError, match="File comment publishing failed"):
            publisher.publish_file_comments(comments, mr_details)

    def test_publish_inline_comment_with_shas(self, publisher, mr_details):
        """Test inline comment publishing with complete SHA info"""
        mock_response = {"id": 123}
        publisher.gitlab_client.post_inline_comment.return_value = mock_response
        
        comment = FormattedComment(
            comment_type=CommentType.ISSUE,
            severity=SeverityLevel.HIGH,
            file_path="src/test.py",
            line_number=42,
            body="Inline comment"
        )
        
        formatted_text = "Formatted comment"
        result = publisher._publish_inline_comment(comment, mr_details, formatted_text)
        
        assert result == mock_response
        publisher.gitlab_client.post_inline_comment.assert_called_once_with(
            body=formatted_text,
            file_path="src/test.py",
            line_number=42,
            base_sha="abc123",
            start_sha="def456",
            head_sha="ghi789",
            old_line=None,
            line_code=None
        )

    def test_publish_inline_comment_missing_shas(self, publisher):
        """Test inline comment publishing with missing SHA info"""
        mock_response = {"id": 123}
        publisher.gitlab_client.post_comment.return_value = mock_response
        
        mr_details = {"diff_refs": {}}  # Missing SHAs
        comment = FormattedComment(
            comment_type=CommentType.ISSUE,
            severity=SeverityLevel.HIGH,
            file_path="src/test.py",
            line_number=42,
            body="Inline comment"
        )
        
        formatted_text = "Formatted comment"
        result = publisher._publish_inline_comment(comment, mr_details, formatted_text)
        
        assert result == mock_response
        # Should fallback to regular post_comment with note
        expected_fallback = f"{formatted_text}\n\n---\n*Note: This comment was intended for `{comment.file_path}:{comment.line_number}`*"
        publisher.gitlab_client.post_comment.assert_called_once_with(expected_fallback)
        publisher.gitlab_client.post_inline_comment.assert_not_called()

    def test_publish_inline_comment_no_diff_refs(self, publisher):
        """Test inline comment publishing with no diff_refs"""
        mock_response = {"id": 123}
        publisher.gitlab_client.post_comment.return_value = mock_response
        
        mr_details = {}  # No diff_refs
        comment = FormattedComment(
            comment_type=CommentType.ISSUE,
            severity=SeverityLevel.HIGH,
            file_path="src/test.py",
            line_number=42,
            body="Inline comment"
        )
        
        formatted_text = "Formatted comment"
        result = publisher._publish_inline_comment(comment, mr_details, formatted_text)

        assert result == mock_response
        # Should fallback to regular post_comment with note
        expected_fallback = f"{formatted_text}\n\n---\n*Note: This comment was intended for `{comment.file_path}:{comment.line_number}`*"
        publisher.gitlab_client.post_comment.assert_called_once_with(expected_fallback)


class TestRateLimiting:
    """Test rate limiting functionality"""

    @pytest.fixture
    def publisher(self, mock_gitlab_client, mock_settings):
        """Create CommentPublisher instance for testing"""
        mock_settings.api_request_delay = 0.1  # Short delay for testing
        with patch('src.comment_publisher.settings', mock_settings):
            return CommentPublisher(gitlab_client=mock_gitlab_client)

    def test_apply_rate_limit_first_call(self, publisher):
        """Test rate limiting on first call (should not sleep)"""
        start_time = time.time()
        publisher._apply_rate_limit()
        end_time = time.time()
        
        # Should not sleep on first call
        assert end_time - start_time < 0.05

    def test_apply_rate_limit_subsequent_calls(self, publisher):
        """Test rate limiting on subsequent calls"""
        # First call to set baseline
        publisher._apply_rate_limit()
        
        # Set last_comment_time to current time so next call will need to wait
        current_time = time.time()
        publisher.last_comment_time = current_time
        
        start_time = time.time()
        publisher._apply_rate_limit()
        end_time = time.time()
        
        # Should sleep for approximately the delay time (0.1s)
        elapsed = end_time - start_time
        assert 0.08 <= elapsed <= 0.15  # Allow for timing variance

    def test_apply_rate_limit_no_wait_needed(self, publisher):
        """Test rate limiting when no wait is needed"""
        # Set last_comment_time to well in the past
        publisher.last_comment_time = time.time() - 1.0  # 1 second ago
        
        start_time = time.time()
        publisher._apply_rate_limit()
        end_time = time.time()
        
        # Should not sleep if enough time has passed
        elapsed = end_time - start_time
        assert elapsed < 0.05


class TestBatchPublishing:
    """Test batch publishing functionality"""

    @pytest.fixture
    def publisher(self, mock_gitlab_client, mock_settings):
        """Create CommentPublisher instance for testing"""
        with patch('src.comment_publisher.settings', mock_settings):
            return CommentPublisher(gitlab_client=mock_gitlab_client)

    @pytest.fixture
    def mr_details(self):
        """Sample MR details for testing"""
        return {
            "id": 456,
            "diff_refs": {
                "base_sha": "abc123",
                "start_sha": "def456",
                "head_sha": "ghi789"
            }
        }

    def test_publish_comment_batch_empty(self, publisher, mr_details):
        """Test publishing empty batch"""
        batch = CommentBatch()
        result = publisher.publish_comment_batch(batch, mr_details)
        
        assert result["summary_published"] is False
        assert result["file_comments_published"] == 0
        assert result["inline_comments_published"] == 0
        assert result["total_comments"] == 0
        assert len(result["errors"]) == 0

    def test_publish_comment_batch_with_summary(self, publisher, mr_details):
        """Test publishing batch with only summary"""
        batch = CommentBatch(summary_comment="Test summary")
        
        # Mock summary publishing
        publisher.publish_review_summary = Mock()
        
        result = publisher.publish_comment_batch(batch, mr_details)
        
        assert result["summary_published"] is True
        assert result["total_comments"] == 0
        publisher.publish_review_summary.assert_called_once_with("Test summary", mr_details)

    def test_publish_comment_batch_with_comments(self, publisher, mr_details):
        """Test publishing batch with file comments"""
        comments = [
            FormattedComment(
                comment_type=CommentType.SUGGESTION,
                severity=SeverityLevel.LOW,
                file_path="src/test.py",
                body="Test comment"
            )
        ]
        batch = CommentBatch(file_comments=comments)
        
        # Mock comment publishing
        publisher.publish_file_comments = Mock(return_value=[{"id": 1}])
        
        result = publisher.publish_comment_batch(batch, mr_details)
        
        assert result["file_comments_published"] == 1
        assert result["total_comments"] == 1
        publisher.publish_file_comments.assert_called_once()

    def test_publish_comment_batch_with_inline_comments(self, publisher, mr_details):
        """Test publishing batch with inline comments"""
        inline_comments = [
            FormattedComment(
                comment_type=CommentType.ISSUE,
                severity=SeverityLevel.HIGH,
                file_path="src/test.py",
                line_number=42,
                body="Inline comment"
            )
        ]
        batch = CommentBatch(inline_comments=inline_comments)
        
        # Mock comment publishing
        publisher.publish_file_comments = Mock(return_value=[{"id": 1}])
        
        result = publisher.publish_comment_batch(batch, mr_details)
        
        assert result["inline_comments_published"] == 1
        assert result["total_comments"] == 1
        publisher.publish_file_comments.assert_called_once()

    def test_publish_comment_batch_mixed(self, publisher, mr_details):
        """Test publishing batch with summary and comments"""
        comments = [
            FormattedComment(
                comment_type=CommentType.SUGGESTION,
                severity=SeverityLevel.LOW,
                file_path="src/test.py",
                body="File comment"
            )
        ]
        inline_comments = [
            FormattedComment(
                comment_type=CommentType.ISSUE,
                severity=SeverityLevel.HIGH,
                file_path="src/test.py",
                line_number=42,
                body="Inline comment"
            )
        ]
        batch = CommentBatch(
            summary_comment="Test summary",
            file_comments=comments,
            inline_comments=inline_comments
        )
        
        # Mock publishing methods
        publisher.publish_review_summary = Mock()
        publisher.publish_file_comments = Mock(return_value=[{"id": 1}, {"id": 2}])
        
        result = publisher.publish_comment_batch(batch, mr_details)
        
        assert result["summary_published"] is True
        assert result["file_comments_published"] == 1
        assert result["inline_comments_published"] == 1
        assert result["total_comments"] == 2

    def test_publish_comment_batch_with_error(self, publisher, mr_details):
        """Test batch publishing with error"""
        batch = CommentBatch(summary_comment="Test summary")
        
        # Mock error in summary publishing
        publisher.publish_review_summary = Mock(side_effect=Exception("API Error"))
        
        result = publisher.publish_comment_batch(batch, mr_details)
        
        assert result["summary_published"] is False
        assert len(result["errors"]) == 1
        assert "Failed to publish comment batch" in result["errors"][0]

    def test_publish_comment_batch_combined_comments(self, publisher, mr_details):
        """Test that file and inline comments are combined for publishing"""
        file_comments = [
            FormattedComment(
                comment_type=CommentType.SUGGESTION,
                severity=SeverityLevel.LOW,
                file_path="src/test.py",
                body="File comment"
            )
        ]
        inline_comments = [
            FormattedComment(
                comment_type=CommentType.ISSUE,
                severity=SeverityLevel.HIGH,
                file_path="src/test.py",
                line_number=42,
                body="Inline comment"
            )
        ]
        batch = CommentBatch(file_comments=file_comments, inline_comments=inline_comments)
        
        # Mock publishing method
        publisher.publish_file_comments = Mock(return_value=[{"id": 1}, {"id": 2}])
        
        result = publisher.publish_comment_batch(batch, mr_details)
        
        # Both comment types should be combined and published together
        publisher.publish_file_comments.assert_called_once()
        call_args = publisher.publish_file_comments.call_args[0][0]
        assert len(call_args) == 2  # Both file and inline comments