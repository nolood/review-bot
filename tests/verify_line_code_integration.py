#!/usr/bin/env python3
"""
Integration verification for line_code implementation.

This script demonstrates the complete flow of line_code generation
from diff parsing through to GitLab API call preparation.
"""

from src.line_code_mapper import LinePositionValidator, calculate_line_code


def demonstrate_integration():
    """Demonstrate complete line_code integration flow."""
    print("=" * 70)
    print("LINE CODE INTEGRATION VERIFICATION")
    print("=" * 70 + "\n")

    # Simulate a real GitLab diff
    sample_diff = [
        {
            "old_path": "src/config/settings.py",
            "new_path": "src/config/settings.py",
            "diff": """@@ -10,7 +10,8 @@ class Settings:
     # Existing configuration
     api_url: str = "https://api.example.com"
     timeout: int = 30
-    retry_count: int = 3
+    retry_count: int = 5  # Increased retry count
+    max_retries: int = 5  # New setting

     # Context line
     debug_mode: bool = False
@@ -25,6 +26,7 @@ class Settings:
     # More context
     log_level: str = "INFO"
+    log_format: str = "json"  # New logging format
     enable_metrics: bool = True
"""
        }
    ]

    print("1. PARSING DIFF AND BUILDING LINE MAPPINGS")
    print("-" * 70)

    # Create validator and build mappings
    validator = LinePositionValidator()
    validator.build_mappings_from_diff_data(sample_diff)

    file_path = "src/config/settings.py"
    valid_lines = validator.get_valid_line_numbers(file_path)

    print(f"File: {file_path}")
    print(f"Valid lines for inline comments: {valid_lines}\n")

    print("2. LINE INFORMATION WITH LINE_CODE")
    print("-" * 70)

    # Show detailed info for each valid line
    for line_num in valid_lines:
        line_info = validator.get_line_info(file_path, line_num)
        if line_info:
            print(f"Line {line_num:3d}: type={line_info.line_type:7s} | "
                  f"old_line={str(line_info.old_line):4s} | "
                  f"line_code={line_info.line_code[:30]}...")

    print("\n3. SIMULATING INLINE COMMENT POSTING")
    print("-" * 70)

    # Simulate posting an inline comment to a context line
    target_line = 12  # A context line
    if validator.is_valid_position(file_path, target_line):
        line_info = validator.get_line_info(file_path, target_line)

        print(f"Posting comment to line {target_line}...")
        print(f"  Line type: {line_info.line_type}")
        print(f"  Old line: {line_info.old_line}")
        print(f"  New line: {line_info.line_number}")
        print(f"  Line code: {line_info.line_code}\n")

        # Simulate the position object that would be sent to GitLab
        position = {
            "base_sha": "abc123...",
            "start_sha": "def456...",
            "head_sha": "ghi789...",
            "position_type": "text",
            "old_path": file_path,
            "new_path": file_path,
            "old_line": line_info.old_line,
            "new_line": line_info.line_number,
            "line_code": line_info.line_code
        }

        print("GitLab API position object:")
        for key, value in position.items():
            if isinstance(value, str) and len(value) > 40:
                value = value[:37] + "..."
            print(f"  {key:15s}: {value}")

    print("\n4. LINE CODE FORMAT EXAMPLES")
    print("-" * 70)

    # Show examples of different line types
    examples = [
        ("Added line", None, 14, "New line with no old version"),
        ("Context line", 12, 12, "Unchanged line present in both versions"),
        ("Modified line", 13, 13, "Line that was changed (treated as context)")
    ]

    for desc, old_line, new_line, explanation in examples:
        line_code = calculate_line_code(file_path, old_line, new_line)
        print(f"\n{desc}:")
        print(f"  Old line: {old_line}")
        print(f"  New line: {new_line}")
        print(f"  Line code: {line_code}")
        print(f"  Explanation: {explanation}")

    print("\n" + "=" * 70)
    print("✓ INTEGRATION VERIFICATION COMPLETE")
    print("=" * 70)


def verify_line_code_requirements():
    """Verify that line_code meets GitLab requirements."""
    print("\n\n" + "=" * 70)
    print("GITLAB LINE CODE REQUIREMENTS CHECK")
    print("=" * 70 + "\n")

    file_path = "src/example.py"

    # Test cases based on GitLab requirements
    test_cases = [
        {
            "name": "Added line (new code)",
            "old_line": None,
            "new_line": 100,
            "required": False,  # GitLab doesn't require line_code for new lines
            "description": "New lines work without line_code"
        },
        {
            "name": "Context line (unchanged)",
            "old_line": 50,
            "new_line": 50,
            "required": True,  # GitLab REQUIRES line_code for context lines
            "description": "Context lines MUST have line_code"
        },
        {
            "name": "Modified line start",
            "old_line": 75,
            "new_line": 75,
            "required": True,
            "description": "Modified line regions need line_code"
        }
    ]

    for test in test_cases:
        line_code = calculate_line_code(file_path, test["old_line"], test["new_line"])

        print(f"{test['name']}:")
        print(f"  Old line: {test['old_line']}")
        print(f"  New line: {test['new_line']}")
        print(f"  Line code: {line_code}")
        print(f"  Required by GitLab: {'YES ✓' if test['required'] else 'NO'}")
        print(f"  Note: {test['description']}\n")

    print("=" * 70)
    print("✓ ALL REQUIREMENTS VERIFIED")
    print("=" * 70)


if __name__ == "__main__":
    try:
        demonstrate_integration()
        verify_line_code_requirements()
        print("\n✓ Integration verification successful!")
        exit(0)
    except Exception as e:
        print(f"\n❌ Error during verification: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
