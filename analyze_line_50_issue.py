#!/usr/bin/env python3
"""
Direct analysis of why line 50 fails while lines 38 and 72 succeed.

Based on the facts provided:
- All 3 lines validated as VALID by LinePositionValidator
- Lines 38 and 72: SUCCESS (201 Created)
- Line 50: FAILURE (400 Bad Request - line_code error)
"""

import sys
sys.path.insert(0, '/home/nolood/general/review-bot')

from src.line_code_mapper import LinePositionValidator

def analyze_issue():
    print("=" * 80)
    print("CRITICAL ISSUE ANALYSIS")
    print("=" * 80)
    print()
    print("FACT: All 3 lines (38, 50, 72) validated as VALID by LinePositionValidator")
    print("FACT: Lines 38 and 72 succeeded (201 Created)")
    print("FACT: Line 50 failed (400 Bad Request - line_code error)")
    print()
    print("This means:")
    print("  1. The validator thinks line 50 is valid")
    print("  2. GitLab API rejects line 50 without line_code")
    print("  3. GitLab API accepts lines 38 and 72 without line_code")
    print()
    print("=" * 80)
    print("HYPOTHESIS: Different line types have different requirements")
    print("=" * 80)
    print()

    # Test hypothesis: Context lines might need line_code, added lines don't
    test_scenarios = [
        {
            "name": "Line 38 is ADDED",
            "diff": """@@ -35,5 +35,6 @@
 line 35
 line 36
 line 37
+line 38
 line 39""",
            "line": 38,
            "expected_type": "added"
        },
        {
            "name": "Line 50 is CONTEXT",
            "diff": """@@ -48,5 +48,5 @@
 line 48
 line 49
 line 50
 line 51
 line 52""",
            "line": 50,
            "expected_type": "context"
        },
        {
            "name": "Line 72 is ADDED",
            "diff": """@@ -70,5 +70,6 @@
 line 70
 line 71
+line 72
 line 73
 line 74""",
            "line": 72,
            "expected_type": "added"
        }
    ]

    for scenario in test_scenarios:
        print(f"\n{scenario['name']}:")
        print(f"  Diff:\n{scenario['diff']}")

        validator = LinePositionValidator()
        diff_data = [{
            "old_path": "deal-relationships.tsx",
            "new_path": "deal-relationships.tsx",
            "diff": scenario["diff"]
        }]
        validator.build_mappings_from_diff_data(diff_data)

        is_valid = validator.is_valid_position("deal-relationships.tsx", scenario["line"])
        line_info = validator.get_line_info("deal-relationships.tsx", scenario["line"])

        print(f"  Is Valid: {is_valid}")
        if line_info:
            print(f"  Line Type: {line_info.line_type}")
            print(f"  Expected Type: {scenario['expected_type']}")
            print(f"  Match: {line_info.line_type == scenario['expected_type']}")
        else:
            print(f"  ERROR: No line info found!")

    print()
    print("=" * 80)
    print("GITLAB API BEHAVIOR (from documentation)")
    print("=" * 80)
    print()
    print("GitLab /discussions endpoint for inline comments:")
    print()
    print("  position: {")
    print("    base_sha: string (required)")
    print("    start_sha: string (required)")
    print("    head_sha: string (required)")
    print("    position_type: 'text' (required)")
    print("    new_path: string (required)")
    print("    old_path: string (required)")
    print("    new_line: integer (line in new file)")
    print("    old_line: integer (line in old file)")
    print("    line_code: string (OPTIONAL but may be required for some lines)")
    print("  }")
    print()
    print("=" * 80)
    print("THE REAL ISSUE")
    print("=" * 80)
    print()
    print("GitLab's line_code is a hash that identifies a specific line in the diff.")
    print("It's calculated from the diff content and uniquely identifies each line.")
    print()
    print("When line_code is needed:")
    print("  - CONTEXT lines: GitLab may require line_code to disambiguate")
    print("  - ADDED lines: Can work without line_code (unambiguous)")
    print("  - REMOVED lines: Only exist in old file, need line_code")
    print()
    print("In our case:")
    print("  - Line 38 (ADDED): Works without line_code ✓")
    print("  - Line 50 (CONTEXT): Requires line_code ✗")
    print("  - Line 72 (ADDED): Works without line_code ✓")
    print()
    print("=" * 80)
    print("SOLUTION")
    print("=" * 80)
    print()
    print("We need to generate line_code for ALL lines, not just some.")
    print()
    print("Line code format (from GitLab source):")
    print("  line_code = sha256(file_path + old_line + new_line).hex()[0:40]")
    print()
    print("Or we need to get it from the diff data GitLab provides.")
    print()
    print("CHECK: Does GitLab's /merge_requests/:id/diffs endpoint return line_code?")
    print()

def check_line_code_in_diff():
    """
    The real question: Does GitLab provide line_code in the diff data?
    """
    print()
    print("=" * 80)
    print("CHECKING: GitLab Diff API Response Structure")
    print("=" * 80)
    print()
    print("Expected structure from GitLab API:")
    print()
    print("GET /api/v4/projects/:id/merge_requests/:iid/diffs")
    print()
    print("[")
    print("  {")
    print('    "old_path": "deal-relationships.tsx",')
    print('    "new_path": "deal-relationships.tsx",')
    print('    "a_mode": "100644",')
    print('    "b_mode": "100644",')
    print('    "new_file": false,')
    print('    "renamed_file": false,')
    print('    "deleted_file": false,')
    print('    "diff": "@@ -35,5 +35,6 @@\\n line 35\\n...",')
    print('    "line_code": "DOES THIS EXIST?"  <--- UNKNOWN')
    print("  }")
    print("]")
    print()
    print("The diff field contains the unified diff text, but does it include")
    print("line_code information for each line?")
    print()
    print("NEED TO CHECK: Real GitLab API response")
    print()

def provide_recommendations():
    print()
    print("=" * 80)
    print("RECOMMENDATIONS FOR INVESTIGATION")
    print("=" * 80)
    print()
    print("1. Examine actual GitLab diff API response:")
    print("   - Check if it includes line_code for each line")
    print("   - Look for any line-specific metadata")
    print()
    print("2. Check GitLab documentation:")
    print("   - When is line_code required vs optional?")
    print("   - How is line_code calculated?")
    print()
    print("3. Test with GitLab API directly:")
    print("   - POST inline comment to ADDED line (should work)")
    print("   - POST inline comment to CONTEXT line without line_code (should fail)")
    print("   - POST inline comment to CONTEXT line WITH line_code (should work)")
    print()
    print("4. Possible solutions:")
    print("   a) Generate line_code ourselves (requires understanding algorithm)")
    print("   b) Extract line_code from GitLab diff response")
    print("   c) Only allow inline comments on ADDED lines (too restrictive)")
    print("   d) Fall back to general comments for CONTEXT lines")
    print()
    print("5. Update LinePositionValidator:")
    print("   - Track line_type (added, context, removed)")
    print("   - Include line_code in LinePositionInfo if available")
    print("   - Return line_code when validating positions")
    print()
    print("6. Update CommentPublisher:")
    print("   - Get line_code from validator")
    print("   - Include line_code in position object for GitLab API")
    print()
    print("=" * 80)
    print("NEXT STEPS")
    print("=" * 80)
    print()
    print("1. Find actual logs/data showing GitLab diff API response")
    print("2. Determine if line_code is available in the response")
    print("3. Implement line_code extraction and usage")
    print()

if __name__ == "__main__":
    analyze_issue()
    check_line_code_in_diff()
    provide_recommendations()
