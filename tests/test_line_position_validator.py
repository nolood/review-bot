"""
Tests for line position validator.

This module tests the functionality of the LinePositionValidator class
to ensure it correctly identifies valid line positions for inline comments.
"""

import pytest
from src.line_code_mapper import LinePositionValidator, FileLineMapping


class TestLinePositionValidator:
    """Test suite for LinePositionValidator."""

    def test_basic_line_validation(self):
        """Test basic line position validation."""
        validator = LinePositionValidator()

        # Sample diff data with a simple change
        diff_data = [
            {
                "old_path": "test.py",
                "new_path": "test.py",
                "diff": """@@ -1,3 +1,4 @@
 def hello():
-    print("old")
+    print("new")
+    print("added line")
 """
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Line 1 (context) should be valid
        assert validator.is_valid_position("test.py", 1)

        # Line 2 (added) should be valid
        assert validator.is_valid_position("test.py", 2)

        # Line 3 (added) should be valid
        assert validator.is_valid_position("test.py", 3)

        # Line 10 (not in diff) should be invalid
        assert not validator.is_valid_position("test.py", 10)

    def test_multiple_files(self):
        """Test validation across multiple files."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "file1.py",
                "new_path": "file1.py",
                "diff": """@@ -1,2 +1,3 @@
 line1
+line2
 line3
"""
            },
            {
                "old_path": "file2.py",
                "new_path": "file2.py",
                "diff": """@@ -5,2 +5,3 @@
 line5
+line6
 line7
"""
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # file1.py validations
        assert validator.is_valid_position("file1.py", 1)
        assert validator.is_valid_position("file1.py", 2)
        assert validator.is_valid_position("file1.py", 3)
        assert not validator.is_valid_position("file1.py", 10)

        # file2.py validations
        assert validator.is_valid_position("file2.py", 5)
        assert validator.is_valid_position("file2.py", 6)
        assert validator.is_valid_position("file2.py", 7)
        assert not validator.is_valid_position("file2.py", 1)

    def test_multiple_hunks(self):
        """Test validation with multiple hunks in a file."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "test.py",
                "new_path": "test.py",
                "diff": """@@ -1,2 +1,3 @@
 line1
+added_line1
 line2
@@ -10,2 +11,3 @@
 line10
+added_line10
 line11
"""
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # First hunk lines
        assert validator.is_valid_position("test.py", 1)
        assert validator.is_valid_position("test.py", 2)
        assert validator.is_valid_position("test.py", 3)

        # Between hunks (not valid)
        assert not validator.is_valid_position("test.py", 5)

        # Second hunk lines
        assert validator.is_valid_position("test.py", 11)
        assert validator.is_valid_position("test.py", 12)
        assert validator.is_valid_position("test.py", 13)

    def test_new_file(self):
        """Test validation for newly added files."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "/dev/null",
                "new_path": "new_file.py",
                "diff": """@@ -0,0 +1,3 @@
+line1
+line2
+line3
"""
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # All lines in new file should be valid
        assert validator.is_valid_position("new_file.py", 1)
        assert validator.is_valid_position("new_file.py", 2)
        assert validator.is_valid_position("new_file.py", 3)

        # Line 4 doesn't exist
        assert not validator.is_valid_position("new_file.py", 4)

    def test_get_valid_line_numbers(self):
        """Test getting all valid line numbers for a file."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "test.py",
                "new_path": "test.py",
                "diff": """@@ -1,3 +1,4 @@
 line1
+line2
 line3
 line4
"""
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        valid_lines = validator.get_valid_line_numbers("test.py")
        assert valid_lines == [1, 2, 3, 4]

    def test_find_nearest_valid_line(self):
        """Test finding nearest valid line."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "test.py",
                "new_path": "test.py",
                "diff": """@@ -1,2 +1,3 @@
 line1
+line2
 line3
@@ -10,2 +11,3 @@
 line10
+line11
 line12
"""
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Line 5 is not in diff, nearest should be line 3
        nearest = validator.find_nearest_valid_line("test.py", 5)
        assert nearest == 3

        # Line 9 is not in diff, nearest should be line 11
        nearest = validator.find_nearest_valid_line("test.py", 9)
        assert nearest == 11

    def test_empty_diff(self):
        """Test validation with empty diff."""
        validator = LinePositionValidator()

        diff_data = []

        validator.build_mappings_from_diff_data(diff_data)

        # Should return False for any file/line
        assert not validator.is_valid_position("test.py", 1)
        assert validator.get_valid_line_numbers("test.py") == []

    def test_line_info_retrieval(self):
        """Test getting detailed line information."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "test.py",
                "new_path": "test.py",
                "diff": """@@ -1,2 +1,3 @@
 line1
+line2
 line3
"""
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Get info for context line
        info = validator.get_line_info("test.py", 1)
        assert info is not None
        assert info.line_number == 1
        assert info.line_type == "context"

        # Get info for added line
        info = validator.get_line_info("test.py", 2)
        assert info is not None
        assert info.line_number == 2
        assert info.line_type == "added"

        # Get info for non-existent line
        info = validator.get_line_info("test.py", 100)
        assert info is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
