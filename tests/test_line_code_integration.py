"""
Integration tests for line_code implementation.

This module provides focused integration tests to verify that the line_code
calculation and integration with LinePositionValidator works correctly,
specifically for the failing scenario with lines 38, 50, and 72.

Tests cover:
- Added lines (line_code format: {sha}__<new>)
- Context lines (line_code format: {sha}_<old>_<new>)
- SHA1 hash calculation for file paths
- Position objects include correct line_code
"""

import pytest
import hashlib
from src.line_code_mapper import (
    LinePositionValidator,
    FileLineMapping,
    LinePositionInfo,
    calculate_line_code,
)


class TestCalculateLineCode:
    """Test suite for the calculate_line_code function."""

    def test_added_line_code_format(self):
        """Test line_code format for added lines (only new_line provided)."""
        file_path = "src/example.py"
        line_code = calculate_line_code(file_path, old_line=None, new_line=38)

        # Calculate expected SHA1
        expected_sha = hashlib.sha1(file_path.encode("utf-8")).hexdigest()
        expected = f"{expected_sha}__{38}"

        assert line_code == expected
        assert line_code.count("_") >= 2  # At least {sha}__{new}

    def test_context_line_code_format(self):
        """Test line_code format for context lines (both old and new lines provided)."""
        file_path = "src/example.py"
        line_code = calculate_line_code(file_path, old_line=35, new_line=50)

        # Calculate expected SHA1
        expected_sha = hashlib.sha1(file_path.encode("utf-8")).hexdigest()
        expected = f"{expected_sha}_{35}_{50}"

        assert line_code == expected

    def test_removed_line_code_format(self):
        """Test line_code format for removed lines (only old_line provided)."""
        file_path = "src/example.py"
        line_code = calculate_line_code(file_path, old_line=45, new_line=None)

        # Calculate expected SHA1
        expected_sha = hashlib.sha1(file_path.encode("utf-8")).hexdigest()
        expected = f"{expected_sha}_{45}_"

        assert line_code == expected

    def test_sha1_calculation_consistency(self):
        """Test that SHA1 calculation is consistent."""
        file_path = "src/module/file.py"
        sha1_1 = hashlib.sha1(file_path.encode("utf-8")).hexdigest()

        # Calculate using the function
        line_code = calculate_line_code(file_path, old_line=1, new_line=2)
        sha1_from_line_code = line_code.split("_")[0]

        assert sha1_1 == sha1_from_line_code
        assert len(sha1_from_line_code) == 40  # SHA1 hex is 40 characters

    def test_different_file_paths_different_sha(self):
        """Test that different file paths produce different SHA1 hashes."""
        file1_code = calculate_line_code("file1.py", old_line=1, new_line=2)
        file2_code = calculate_line_code("file2.py", old_line=1, new_line=2)

        sha1_1 = file1_code.split("_")[0]
        sha1_2 = file2_code.split("_")[0]

        assert sha1_1 != sha1_2

    def test_invalid_file_path_empty(self):
        """Test that empty file path raises ValueError."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            calculate_line_code("", old_line=None, new_line=1)

    def test_invalid_file_path_whitespace(self):
        """Test that whitespace-only file path raises ValueError."""
        with pytest.raises(ValueError, match="file_path cannot be empty"):
            calculate_line_code("   ", old_line=None, new_line=1)

    def test_invalid_no_line_numbers(self):
        """Test that providing neither old_line nor new_line raises ValueError."""
        with pytest.raises(
            ValueError,
            match="At least one of old_line or new_line must be provided",
        ):
            calculate_line_code("file.py", old_line=None, new_line=None)

    def test_invalid_negative_old_line(self):
        """Test that negative old_line raises ValueError."""
        with pytest.raises(ValueError, match="old_line must be non-negative"):
            calculate_line_code("file.py", old_line=-1, new_line=5)

    def test_invalid_negative_new_line(self):
        """Test that negative new_line raises ValueError."""
        with pytest.raises(ValueError, match="new_line must be non-negative"):
            calculate_line_code("file.py", old_line=5, new_line=-1)

    def test_zero_line_numbers(self):
        """Test that zero line numbers are valid (they represent positions)."""
        # Zero should be valid as it might represent a special position
        line_code = calculate_line_code("file.py", old_line=0, new_line=0)
        assert "_0_0" in line_code


class TestLinePositionInfoLineCode:
    """Test suite for line_code in LinePositionInfo objects."""

    def test_line_position_info_includes_line_code(self):
        """Test that LinePositionInfo objects include line_code."""
        file_path = "src/example.py"
        line_code = calculate_line_code(file_path, old_line=None, new_line=38)

        info = LinePositionInfo(
            file_path=file_path,
            line_number=38,
            old_line=None,
            line_type="added",
            in_diff_hunk=True,
            line_code=line_code,
        )

        assert info.line_code == line_code
        assert info.line_number == 38
        assert info.line_type == "added"
        assert info.old_line is None

    def test_line_position_info_for_context_line(self):
        """Test LinePositionInfo for context line with old and new line numbers."""
        file_path = "src/example.py"
        old_line = 35
        new_line = 50
        line_code = calculate_line_code(file_path, old_line=old_line, new_line=new_line)

        info = LinePositionInfo(
            file_path=file_path,
            line_number=new_line,
            old_line=old_line,
            line_type="context",
            in_diff_hunk=True,
            line_code=line_code,
        )

        assert info.line_code == line_code
        assert info.old_line == old_line
        assert info.line_number == new_line
        assert info.line_type == "context"


class TestFileLineMappingLineCode:
    """Test suite for line_code integration in FileLineMapping."""

    def test_add_valid_line_generates_line_code(self):
        """Test that adding a valid line generates correct line_code."""
        file_path = "src/example.py"
        mapping = FileLineMapping(file_path=file_path)

        # Add an added line (no old_line)
        mapping.add_valid_line(line_number=38, old_line=None, line_type="added")

        # Get line info and verify line_code
        info = mapping.get_line_info(38)
        assert info is not None
        assert info.line_code == calculate_line_code(
            file_path, old_line=None, new_line=38
        )

    def test_add_context_line_generates_line_code(self):
        """Test that adding a context line generates correct line_code."""
        file_path = "src/example.py"
        mapping = FileLineMapping(file_path=file_path)

        # Add a context line with both old and new line numbers
        mapping.add_valid_line(line_number=50, old_line=35, line_type="context")

        # Get line info and verify line_code
        info = mapping.get_line_info(50)
        assert info is not None
        expected_code = calculate_line_code(
            file_path, old_line=35, new_line=50
        )
        assert info.line_code == expected_code

    def test_file_sha_property(self):
        """Test that FileLineMapping correctly caches file SHA."""
        file_path = "src/module/file.py"
        mapping = FileLineMapping(file_path=file_path)

        # Get file_sha
        sha1 = mapping.file_sha

        # Verify it matches expected value
        expected_sha = hashlib.sha1(file_path.encode("utf-8")).hexdigest()
        assert sha1 == expected_sha
        assert len(sha1) == 40


class TestLinePositionValidatorLineCode:
    """Test suite for line_code with LinePositionValidator."""

    def test_added_line_38_scenario(self):
        """Test the specific failing scenario: added line at 38."""
        validator = LinePositionValidator()

        # Create diff data with an added line at line 38
        diff_data = [
            {
                "old_path": "src/example.py",
                "new_path": "src/example.py",
                "diff": """@@ -35,5 +35,6 @@
 # Line 35: context
 # Line 36: context
 # Line 37: context
+# Line 38: ADDED
 # Line 39: context
 # Line 40: context
""",
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Verify line 38 is valid
        assert validator.is_valid_position("src/example.py", 38)

        # Get line info and verify line_code
        info = validator.get_line_info("src/example.py", 38)
        assert info is not None
        assert info.line_type == "added"
        assert info.old_line is None
        assert info.line_number == 38

        # Verify line_code format
        expected_code = calculate_line_code(
            "src/example.py", old_line=None, new_line=38
        )
        assert info.line_code == expected_code

    def test_context_line_50_scenario(self):
        """Test the specific failing scenario: context line at 50."""
        validator = LinePositionValidator()

        # Create diff data with a context line at line 50
        diff_data = [
            {
                "old_path": "src/example.py",
                "new_path": "src/example.py",
                "diff": """@@ -48,5 +48,5 @@
 # Line 48: context
 # Line 49: context
 # Line 50: context
 # Line 51: context
 # Line 52: context
""",
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Verify line 50 is valid
        assert validator.is_valid_position("src/example.py", 50)

        # Get line info and verify line_code
        info = validator.get_line_info("src/example.py", 50)
        assert info is not None
        assert info.line_type == "context"
        assert info.old_line == 50  # For context lines, old_line == new_line
        assert info.line_number == 50

        # Verify line_code format
        expected_code = calculate_line_code(
            "src/example.py", old_line=50, new_line=50
        )
        assert info.line_code == expected_code

    def test_added_line_72_scenario(self):
        """Test the specific failing scenario: added line at 72."""
        validator = LinePositionValidator()

        # Create diff data with an added line at line 72
        diff_data = [
            {
                "old_path": "src/example.py",
                "new_path": "src/example.py",
                "diff": """@@ -70,5 +70,6 @@
 # Line 70: context
 # Line 71: context
+# Line 72: ADDED
 # Line 73: context
 # Line 74: context
 # Line 75: context
""",
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Verify line 72 is valid
        assert validator.is_valid_position("src/example.py", 72)

        # Get line info and verify line_code
        info = validator.get_line_info("src/example.py", 72)
        assert info is not None
        assert info.line_type == "added"
        assert info.old_line is None
        assert info.line_number == 72

        # Verify line_code format
        expected_code = calculate_line_code(
            "src/example.py", old_line=None, new_line=72
        )
        assert info.line_code == expected_code

    def test_multiple_hunks_line_code_consistency(self):
        """Test that line_code is consistent across multiple hunks."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "src/example.py",
                "new_path": "src/example.py",
                "diff": """@@ -35,4 +35,5 @@
 # Line 35: context
 # Line 36: context
 # Line 37: context
+# Line 38: ADDED
 # Line 39: context
@@ -50,2 +51,2 @@
 # Line 50: context
 # Line 51: context
""",
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Test that added and context lines have correct line_code
        # Line 38: added
        info_38 = validator.get_line_info("src/example.py", 38)
        assert info_38 is not None
        assert info_38.line_type == "added"
        assert info_38.old_line is None
        assert info_38.line_code == calculate_line_code(
            "src/example.py", old_line=None, new_line=38
        )

        # Line 50: context - first hunk also has line 35-39
        info_35 = validator.get_line_info("src/example.py", 35)
        assert info_35 is not None
        assert info_35.line_type == "context"
        # Verify line_code is properly formatted for context line
        assert info_35.line_code is not None
        assert "_" in info_35.line_code
        # Should be {sha}_<old>_<new> format for context lines
        assert info_35.line_code.count("_") >= 2

        # Line 51: context from second hunk
        info_51 = validator.get_line_info("src/example.py", 51)
        assert info_51 is not None
        assert info_51.line_type == "context"
        # All lines should have line_code
        assert info_51.line_code is not None

    def test_line_code_in_all_valid_lines(self):
        """Test that all valid lines have line_code populated."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "test.py",
                "new_path": "test.py",
                "diff": """@@ -1,5 +1,6 @@
 def hello():
+    pass
     print("hello")
 def world():
     return 42
""",
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Get all valid lines
        valid_lines = validator.get_valid_line_numbers("test.py")
        assert len(valid_lines) > 0

        # Verify every valid line has line_code
        for line_num in valid_lines:
            info = validator.get_line_info("test.py", line_num)
            assert info is not None
            assert info.line_code is not None
            assert len(info.line_code) > 0
            # Line code should contain SHA1 (40 chars) and line numbers separated by _
            assert "_" in info.line_code

    def test_line_code_format_for_mixed_lines(self):
        """Test line_code format for a mix of added, removed, and context lines."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "mixed.py",
                "new_path": "mixed.py",
                "diff": """@@ -1,5 +1,5 @@
 context1
-removed1
+added1
 context2
 context3
""",
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Context lines should have format: {sha}_{old}_{new}
        info_context1 = validator.get_line_info("mixed.py", 1)
        assert info_context1 is not None
        sha = hashlib.sha1("mixed.py".encode("utf-8")).hexdigest()
        assert info_context1.line_code.startswith(sha)
        assert info_context1.line_code.count("_") == 2
        parts = info_context1.line_code.split("_")
        assert parts[1] == "1" and parts[2] == "1"  # {sha}_1_1

        # Added line should have format: {sha}__{new}
        info_added = validator.get_line_info("mixed.py", 2)
        assert info_added is not None
        assert info_added.line_code.startswith(sha)
        # Should have double underscore after SHA
        assert "__" in info_added.line_code or (
            info_added.line_code.count("_") == 2
            and "" in info_added.line_code.split("_")
        )

        # Context2 and context3 should have old and new line numbers
        info_context2 = validator.get_line_info("mixed.py", 3)
        assert info_context2 is not None
        assert info_context2.line_code.count("_") == 2


class TestLineCodeEdgeCases:
    """Test edge cases for line_code implementation."""

    def test_line_code_with_special_characters_in_path(self):
        """Test line_code calculation with special characters in file path."""
        file_path = "src/module/file-name_v2.py"
        line_code = calculate_line_code(file_path, old_line=1, new_line=2)

        # Should still produce valid SHA1
        sha = hashlib.sha1(file_path.encode("utf-8")).hexdigest()
        assert line_code.startswith(sha)

    def test_line_code_with_unicode_path(self):
        """Test line_code calculation with unicode characters in path."""
        file_path = "src/module/файл.py"
        line_code = calculate_line_code(file_path, old_line=1, new_line=2)

        # Should still produce valid SHA1
        sha = hashlib.sha1(file_path.encode("utf-8")).hexdigest()
        assert line_code.startswith(sha)

    def test_line_code_consistency_across_runs(self):
        """Test that line_code is consistent across multiple calculations."""
        file_path = "src/example.py"

        code1 = calculate_line_code(file_path, old_line=10, new_line=20)
        code2 = calculate_line_code(file_path, old_line=10, new_line=20)
        code3 = calculate_line_code(file_path, old_line=10, new_line=20)

        # All should be identical
        assert code1 == code2 == code3

    def test_large_line_numbers(self):
        """Test line_code with very large line numbers."""
        file_path = "src/example.py"
        line_code = calculate_line_code(file_path, old_line=999999, new_line=1000000)

        # Should still be valid
        assert "_999999_1000000" in line_code

    def test_validator_get_line_info_returns_none_for_invalid(self):
        """Test that get_line_info returns None for invalid lines."""
        validator = LinePositionValidator()

        diff_data = [
            {
                "old_path": "test.py",
                "new_path": "test.py",
                "diff": """@@ -1,2 +1,2 @@
 line1
 line2
""",
            }
        ]

        validator.build_mappings_from_diff_data(diff_data)

        # Valid line should return info
        assert validator.get_line_info("test.py", 1) is not None

        # Invalid line should return None
        assert validator.get_line_info("test.py", 100) is None

        # Non-existent file should return None
        assert validator.get_line_info("nonexistent.py", 1) is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
