#!/usr/bin/env python3
"""
Investigation script to understand why line 50 fails while lines 38 and 72 succeed.

This script simulates different diff scenarios to understand GitLab's line_code requirements.
"""

from src.line_code_mapper import LinePositionValidator

# Test different diff scenarios
test_scenarios = [
    {
        "name": "All added lines (new file)",
        "diff": """@@ -0,0 +1,80 @@
+line 1
+line 2
+line 38 - added
+line 39
+line 50 - added
+line 51
+line 72 - added
+line 73""",
        "expected_valid": [1, 2, 38, 39, 50, 51, 72, 73]
    },
    {
        "name": "Context lines only",
        "diff": """@@ -35,50 +35,50 @@
 line 35 - context
 line 36 - context
 line 37 - context
 line 38 - context
 line 39 - context
 line 40 - context
 line 50 - context
 line 51 - context
 line 72 - context
 line 73 - context""",
        "expected_valid": [35, 36, 37, 38, 39, 40, 50, 51, 72, 73]
    },
    {
        "name": "Mixed: lines 38 and 72 are added, line 50 is context",
        "diff": """@@ -35,10 +35,10 @@
 line 35
 line 36
 line 37
+line 38 - ADDED
 line 39
@@ -45,8 +45,8 @@
 line 45
 line 46
 line 47
 line 48
 line 49
 line 50 - CONTEXT
 line 51
 line 52
@@ -68,8 +68,8 @@
 line 68
 line 69
 line 70
 line 71
+line 72 - ADDED
 line 73
 line 74""",
        "expected_valid": [35, 36, 37, 38, 39, 45, 46, 47, 48, 49, 50, 51, 52, 68, 69, 70, 71, 72, 73, 74]
    },
    {
        "name": "Lines 38 and 72 in diff hunks, line 50 NOT in diff hunks",
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
 line 74""",
        "expected_valid": [35, 36, 37, 38, 39, 68, 69, 70, 71, 72, 73, 74],
        "not_valid": [50]  # Line 50 is NOT in any hunk
    },
    {
        "name": "Gaps between hunks - line 50 between two separate hunks",
        "diff": """@@ -35,3 +35,4 @@
 line 35
 line 36
+line 37 - ADDED
 line 38 - CONTEXT
@@ -70,3 +71,3 @@
 line 70
 line 71
+line 72 - ADDED""",
        "expected_valid": [35, 36, 37, 38, 70, 71, 72],
        "not_valid": [50]  # Line 50 is between hunks, not in diff
    }
]

def run_investigation():
    print("=" * 80)
    print("INVESTIGATING: Why line 50 fails while lines 38 and 72 succeed")
    print("=" * 80)
    print()

    for scenario in test_scenarios:
        print(f"\n{'=' * 80}")
        print(f"SCENARIO: {scenario['name']}")
        print(f"{'=' * 80}")

        # Create validator
        validator = LinePositionValidator()

        # Build mapping from diff
        diff_data = [{
            "old_path": "deal-relationships.tsx",
            "new_path": "deal-relationships.tsx",
            "diff": scenario["diff"]
        }]

        validator.build_mappings_from_diff_data(diff_data)

        # Get valid lines
        valid_lines = validator.get_valid_line_numbers("deal-relationships.tsx")

        print(f"\nDiff content:")
        print(scenario["diff"])

        print(f"\nValid lines found: {valid_lines}")
        print(f"Expected valid: {scenario.get('expected_valid', 'Not specified')}")

        # Check specific lines
        print(f"\nLine checks:")
        for line_num in [38, 50, 72]:
            is_valid = validator.is_valid_position("deal-relationships.tsx", line_num)
            line_info = validator.get_line_info("deal-relationships.tsx", line_num)

            status = "✓ VALID" if is_valid else "✗ INVALID"
            line_type = line_info.line_type if line_info else "N/A"

            print(f"  Line {line_num}: {status} (type: {line_type})")

        # Check if scenario matches expected
        if "not_valid" in scenario:
            print(f"\nExpected INVALID lines: {scenario['not_valid']}")
            for line_num in scenario["not_valid"]:
                is_valid = validator.is_valid_position("deal-relationships.tsx", line_num)
                if is_valid:
                    print(f"  ⚠ WARNING: Line {line_num} is VALID but should be INVALID")
                else:
                    print(f"  ✓ Line {line_num} is correctly INVALID")

    print("\n" + "=" * 80)
    print("ANALYSIS COMPLETE")
    print("=" * 80)
    print()
    print("KEY INSIGHT:")
    print("If line 50 FAILS while lines 38 and 72 SUCCEED, it likely means:")
    print("  1. Lines 38 and 72 are IN diff hunks (added/context lines)")
    print("  2. Line 50 is NOT in any diff hunk")
    print("  3. GitLab requires line_code for lines NOT in hunks")
    print("  4. The LinePositionValidator correctly identifies line 50 as invalid")
    print()
    print("EXPECTED BEHAVIOR:")
    print("  - Lines 38, 72: Should be VALID (in diff hunks)")
    print("  - Line 50: Should be INVALID (not in diff hunks)")
    print()
    print("QUESTION TO ANSWER:")
    print("  Why does GitLab accept lines 38 and 72 without line_code,")
    print("  but reject line 50 saying line_code is required?")
    print()
    print("HYPOTHESIS:")
    print("  GitLab's /discussions endpoint:")
    print("    - Accepts position without line_code for lines IN diff hunks")
    print("    - Rejects position without line_code for lines NOT in diff hunks")
    print("  This is the expected behavior - the validator should catch this!")
    print()

if __name__ == "__main__":
    run_investigation()
