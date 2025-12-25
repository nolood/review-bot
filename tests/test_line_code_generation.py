#!/usr/bin/env python3
"""
Test script to calculate GitLab line_code correctly.

Based on GitLab's format: line_code = <SHA>_<old>_<new>
Where SHA is the SHA1 hash of the filename.
"""

import hashlib

def generate_line_code(file_path: str, old_line: int | None, new_line: int | None) -> str:
    """
    Generate GitLab line_code for a specific line position.

    Args:
        file_path: Path to the file (e.g., "deal-relationships.tsx")
        old_line: Line number in old file (None for added lines)
        new_line: Line number in new file (None for removed lines)

    Returns:
        GitLab line_code string in format: <SHA1>_<old>_<new>
    """
    # Calculate SHA1 hash of the file path
    sha1_hash = hashlib.sha1(file_path.encode('utf-8')).hexdigest()

    # Format old and new line numbers
    old_str = str(old_line) if old_line is not None else ""
    new_str = str(new_line) if new_line is not None else ""

    # Construct line_code
    line_code = f"{sha1_hash}_{old_str}_{new_str}"

    return line_code


def test_line_code_generation():
    """Test line_code generation with examples."""

    print("=" * 80)
    print("GITLAB LINE_CODE GENERATION TEST")
    print("=" * 80)
    print()

    # Test cases based on our scenario
    file_path = "deal-relationships.tsx"

    test_cases = [
        {
            "description": "Line 38 - ADDED line (no old_line)",
            "old_line": None,
            "new_line": 38,
            "expected_pattern": f"<SHA1>__38"
        },
        {
            "description": "Line 50 - CONTEXT line (has both old and new)",
            "old_line": 50,
            "new_line": 50,
            "expected_pattern": f"<SHA1>_50_50"
        },
        {
            "description": "Line 72 - ADDED line (no old_line)",
            "old_line": None,
            "new_line": 72,
            "expected_pattern": f"<SHA1>__72"
        },
        {
            "description": "Line 100 - REMOVED line (no new_line)",
            "old_line": 100,
            "new_line": None,
            "expected_pattern": f"<SHA1>_100_"
        }
    ]

    # Calculate SHA1 for reference
    sha1 = hashlib.sha1(file_path.encode('utf-8')).hexdigest()
    print(f"File: {file_path}")
    print(f"SHA1 Hash: {sha1}")
    print()

    for test in test_cases:
        line_code = generate_line_code(
            file_path,
            test["old_line"],
            test["new_line"]
        )

        print(f"{test['description']}:")
        print(f"  old_line: {test['old_line']}")
        print(f"  new_line: {test['new_line']}")
        print(f"  line_code: {line_code}")
        print(f"  Expected pattern: {test['expected_pattern']}")
        print()

    print("=" * 80)
    print("ANALYSIS")
    print("=" * 80)
    print()
    print("GitLab line_code format: <SHA1_of_filename>_<old_line>_<new_line>")
    print()
    print("For our specific case:")
    print(f"  - Line 38 (ADDED): {generate_line_code(file_path, None, 38)}")
    print(f"  - Line 50 (CONTEXT): {generate_line_code(file_path, 50, 50)}")
    print(f"  - Line 72 (ADDED): {generate_line_code(file_path, None, 72)}")
    print()
    print("=" * 80)
    print("WHY LINE 50 FAILS")
    print("=" * 80)
    print()
    print("Based on the investigation:")
    print()
    print("1. Lines 38 and 72 are ADDED lines:")
    print("   - GitLab accepts position without line_code")
    print("   - position: { new_line: 38, old_line: null, ... }")
    print("   - Result: 201 Created ✓")
    print()
    print("2. Line 50 is a CONTEXT line:")
    print("   - GitLab REQUIRES line_code for context lines")
    print("   - position: { new_line: 50, old_line: null, ... }")
    print("   - Missing: line_code")
    print("   - Result: 400 Bad Request - line_code can't be blank ✗")
    print()
    print("3. The fix:")
    print("   - Calculate line_code for ALL lines")
    print("   - Include line_code in position object")
    print("   - position: { new_line: 50, old_line: 50, line_code: '...', ... }")
    print("   - Result: 201 Created ✓")
    print()
    print("=" * 80)
    print("IMPLEMENTATION PLAN")
    print("=" * 80)
    print()
    print("1. Update LinePositionValidator:")
    print("   - Store old_line for each valid line")
    print("   - Calculate and store line_code")
    print("   - Return line_code when validating positions")
    print()
    print("2. Update gitlab_client.py post_inline_comment():")
    print("   - Add line_code parameter")
    print("   - Include line_code in position object")
    print()
    print("3. Update comment_publisher.py _publish_inline_comment():")
    print("   - Get line_code from validator")
    print("   - Pass line_code to gitlab_client")
    print()
    print("4. Test with all three line types:")
    print("   - ADDED lines (line_code optional but can include)")
    print("   - CONTEXT lines (line_code REQUIRED)")
    print("   - REMOVED lines (line_code REQUIRED)")
    print()


if __name__ == "__main__":
    test_line_code_generation()
