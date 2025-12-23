#!/usr/bin/env python3
"""
Debug script to check if the LinePositionValidator is working correctly
and why line 50 might still be reaching GitLab API despite validation.
"""

from src.line_code_mapper import LinePositionValidator
from src.comment_publisher import CommentPublisher, FormattedComment, CommentType, SeverityLevel
from unittest.mock import Mock, MagicMock
import json

def test_validator_integration():
    """Test if the validator correctly prevents invalid line comments."""

    print("=" * 80)
    print("TESTING: LinePositionValidator Integration")
    print("=" * 80)
    print()

    # Create a realistic diff where line 50 is NOT in hunks
    diff_data = [{
        "old_path": "deal-relationships.tsx",
        "new_path": "deal-relationships.tsx",
        "diff": """@@ -35,5 +35,5 @@
 line 35
 line 36
 line 37
+line 38 - ADDED
 line 39
@@ -68,5 +68,5 @@
 line 68
 line 69
 line 70
 line 71
+line 72 - ADDED
 line 73
 line 74"""
    }]

    # Initialize validator
    print("1. Initializing LinePositionValidator...")
    validator = LinePositionValidator()
    validator.build_mappings_from_diff_data(diff_data)
    print(f"   Valid lines: {validator.get_valid_line_numbers('deal-relationships.tsx')}")
    print()

    # Check specific lines
    print("2. Checking line validity:")
    for line_num in [38, 50, 72]:
        is_valid = validator.is_valid_position("deal-relationships.tsx", line_num)
        print(f"   Line {line_num}: {'VALID ✓' if is_valid else 'INVALID ✗'}")
    print()

    # Create mock GitLab client
    print("3. Creating CommentPublisher with validator...")
    mock_gitlab = Mock()
    mock_gitlab.post_comment = Mock(return_value={"id": 123, "body": "test"})
    mock_gitlab.post_inline_comment = Mock()

    publisher = CommentPublisher(
        gitlab_client=mock_gitlab,
        line_position_validator=validator
    )
    print(f"   Publisher has validator: {publisher.line_position_validator is not None}")
    print()

    # MR details with SHAs
    mr_details = {
        "diff_refs": {
            "base_sha": "abc123",
            "start_sha": "def456",
            "head_sha": "ghi789"
        }
    }

    # Test publishing comments for all three lines
    print("4. Attempting to publish inline comments:")
    print()

    for line_num in [38, 50, 72]:
        print(f"   Testing Line {line_num}:")

        comment = FormattedComment(
            comment_type=CommentType.SUGGESTION,
            severity=SeverityLevel.LOW,
            file_path="deal-relationships.tsx",
            line_number=line_num,
            title=f"Comment for line {line_num}",
            body=f"This is a comment for line {line_num}"
        )

        # Reset mocks
        mock_gitlab.post_comment.reset_mock()
        mock_gitlab.post_inline_comment.reset_mock()

        try:
            # Publish the comment
            responses = publisher.publish_file_comments([comment], mr_details)

            # Check what was called
            if mock_gitlab.post_inline_comment.called:
                print(f"     → Called post_inline_comment (inline comment)")
                call_args = mock_gitlab.post_inline_comment.call_args
                print(f"       Args: {call_args}")
            elif mock_gitlab.post_comment.called:
                print(f"     → Called post_comment (general comment - FALLBACK)")
                call_args = mock_gitlab.post_comment.call_args
                body = call_args[0][0] if call_args[0] else ""
                if "not part of the diff" in body:
                    print(f"       ✓ Correctly used fallback for invalid line")
                else:
                    print(f"       Body preview: {body[:100]}...")
            else:
                print(f"     → No API call made!")

        except Exception as e:
            print(f"     → Error: {e}")

        print()

    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    print("Expected behavior:")
    print("  - Line 38: Should call post_inline_comment (VALID)")
    print("  - Line 50: Should call post_comment with fallback message (INVALID)")
    print("  - Line 72: Should call post_inline_comment (VALID)")
    print()
    print("If line 50 is calling post_inline_comment, there's a bug in the validator!")
    print()

def check_validator_state():
    """Check the actual state during comment publishing."""

    print("=" * 80)
    print("CHECKING: Validator State During Publishing")
    print("=" * 80)
    print()

    # Simulate the exact scenario from the user's description
    diff_data = [{
        "old_path": "deal-relationships.tsx",
        "new_path": "deal-relationships.tsx",
        "diff": """@@ -1,100 +1,100 @@
 context line"""  # Minimal diff for testing
    }]

    validator = LinePositionValidator()
    validator.build_mappings_from_diff_data(diff_data)

    print("Checking if validator has the file mapping:")
    has_mapping = validator.has_mapping("deal-relationships.tsx")
    print(f"  Has mapping for 'deal-relationships.tsx': {has_mapping}")
    print()

    if has_mapping:
        valid_lines = validator.get_valid_line_numbers("deal-relationships.tsx")
        print(f"  Valid lines count: {len(valid_lines)}")
        print(f"  Valid lines (first 20): {valid_lines[:20]}")
        print()

    # Check the specific lines
    print("Checking specific lines:")
    for file_path_variant in [
        "deal-relationships.tsx",
        "src/deal-relationships.tsx",
        "/deal-relationships.tsx",
        "./deal-relationships.tsx"
    ]:
        print(f"\n  File path: '{file_path_variant}'")
        has_map = validator.has_mapping(file_path_variant)
        print(f"    Has mapping: {has_map}")

        if has_map:
            for line in [38, 50, 72]:
                is_valid = validator.is_valid_position(file_path_variant, line)
                print(f"    Line {line}: {'VALID' if is_valid else 'INVALID'}")

    print()
    print("=" * 80)
    print("POTENTIAL ISSUE:")
    print("=" * 80)
    print()
    print("If the file paths don't match exactly between:")
    print("  - The diff data (e.g., 'deal-relationships.tsx')")
    print("  - The GLM response (e.g., 'src/deal-relationships.tsx')")
    print()
    print("Then the validator won't find the mapping and will return False,")
    print("but the CommentPublisher might still try to post the inline comment!")
    print()

if __name__ == "__main__":
    test_validator_integration()
    print("\n" * 2)
    check_validator_state()
