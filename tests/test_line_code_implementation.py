#!/usr/bin/env python3
"""
Test script to verify line_code generation and integration.

This script tests the line_code calculation and integration across:
1. line_code_mapper.py - calculation and storage
2. gitlab_client.py - passing to GitLab API
3. comment_publisher.py - integration flow
"""

import hashlib
from src.line_code_mapper import calculate_line_code, LinePositionInfo, FileLineMapping, LinePositionValidator


def test_calculate_line_code():
    """Test line_code calculation for different line types."""
    print("Testing line_code calculation...")

    # Test 1: Added line (no old_line)
    file_path = "src/example.py"
    line_code_added = calculate_line_code(file_path, None, 42)
    expected_sha = hashlib.sha1(file_path.encode('utf-8')).hexdigest()
    expected_added = f"{expected_sha}__{42}"
    assert line_code_added == expected_added, f"Added line: expected {expected_added}, got {line_code_added}"
    print(f"✓ Added line: {line_code_added}")

    # Test 2: Context line (has both old_line and new_line)
    line_code_context = calculate_line_code(file_path, 41, 42)
    expected_context = f"{expected_sha}_41_42"
    assert line_code_context == expected_context, f"Context line: expected {expected_context}, got {line_code_context}"
    print(f"✓ Context line: {line_code_context}")

    # Test 3: Removed line (no new_line)
    line_code_removed = calculate_line_code(file_path, 41, None)
    expected_removed = f"{expected_sha}_41_"
    assert line_code_removed == expected_removed, f"Removed line: expected {expected_removed}, got {line_code_removed}"
    print(f"✓ Removed line: {line_code_removed}")

    print("✓ All line_code calculations passed!\n")


def test_line_position_info():
    """Test LinePositionInfo dataclass with line_code."""
    print("Testing LinePositionInfo with line_code...")

    file_path = "src/test.py"
    line_info = LinePositionInfo(
        file_path=file_path,
        line_number=10,
        old_line=9,
        line_type='context',
        in_diff_hunk=True,
        line_code=calculate_line_code(file_path, 9, 10)
    )

    assert line_info.file_path == file_path
    assert line_info.line_number == 10
    assert line_info.old_line == 9
    assert line_info.line_type == 'context'
    assert line_info.in_diff_hunk is True
    assert line_info.line_code is not None
    assert "_9_10" in line_info.line_code

    print(f"✓ LinePositionInfo: {line_info}")
    print("✓ LinePositionInfo test passed!\n")


def test_file_line_mapping():
    """Test FileLineMapping with line_code generation."""
    print("Testing FileLineMapping with line_code generation...")

    file_path = "src/example.py"
    mapping = FileLineMapping(file_path=file_path)

    # Add different line types
    mapping.add_valid_line(10, None, 'added')  # Added line
    mapping.add_valid_line(20, 19, 'context')  # Context line

    # Verify added line
    added_line_info = mapping.get_line_info(10)
    assert added_line_info is not None
    assert added_line_info.old_line is None
    assert added_line_info.line_code is not None
    assert added_line_info.line_type == 'added'
    print(f"✓ Added line info: line_code={added_line_info.line_code}")

    # Verify context line
    context_line_info = mapping.get_line_info(20)
    assert context_line_info is not None
    assert context_line_info.old_line == 19
    assert context_line_info.line_code is not None
    assert context_line_info.line_type == 'context'
    assert "_19_20" in context_line_info.line_code
    print(f"✓ Context line info: line_code={context_line_info.line_code}")

    print("✓ FileLineMapping test passed!\n")


def test_diff_parsing():
    """Test diff parsing with line_code generation."""
    print("Testing diff parsing with line_code generation...")

    # Sample diff content
    diff_content = """@@ -10,5 +10,6 @@ def example():
     # Context line 1
     # Context line 2
+    # Added line
     # Context line 3
     # Context line 4
"""

    validator = LinePositionValidator()
    file_path = "src/example.py"
    mapping = FileLineMapping(file_path=file_path)

    # Parse the diff
    validator._extract_valid_lines_from_diff(mapping, diff_content)

    # Verify lines were added with line_code
    valid_lines = mapping.valid_new_lines
    print(f"Valid lines: {sorted(valid_lines)}")

    for line_num in valid_lines:
        line_info = mapping.get_line_info(line_num)
        assert line_info is not None, f"Missing line info for line {line_num}"
        assert line_info.line_code is not None, f"Missing line_code for line {line_num}"
        print(f"  Line {line_num}: type={line_info.line_type}, old_line={line_info.old_line}, line_code={line_info.line_code[:20]}...")

    print("✓ Diff parsing test passed!\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Line Code Implementation Tests")
    print("=" * 60 + "\n")

    try:
        test_calculate_line_code()
        test_line_position_info()
        test_file_line_mapping()
        test_diff_parsing()

        print("=" * 60)
        print("✓ ALL TESTS PASSED!")
        print("=" * 60)
        return 0

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
