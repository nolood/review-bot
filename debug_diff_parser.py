#!/usr/bin/env python3
import sys
import os
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

import diff_parser as diff_parser_module

# Create test data
diff_data = [{
    "old_path": "src/main.py",
    "new_path": "src/main.py",
    "new_file": False,
    "deleted_file": False,
    "a_mode": "100644",
    "b_mode": "100644",
    "binary_file": False,
    "diff": """@@ -1,5 +1,7 @@
 def hello_world():
 -    print("Hello, World!")
 +    print("Hello, Enhanced World!")
 +    # Added a comment
 +    return True
 
 if __name__ == "__main__":
"""
}]

# Parse the diff
parser = diff_parser_module.DiffParser()
file_diffs = parser.parse_gitlab_diff(diff_data)

print(f"Number of file diffs: {len(file_diffs)}")
for i, file_diff in enumerate(file_diffs):
    print(f"File {i}: {file_diff.file_path}")
    print(f"  Change type: {file_diff.change_type}")
    print(f"  Added lines: {file_diff.added_lines}")
    print(f"  Removed lines: {file_diff.removed_lines}")
    print(f"  Hunks: {len(file_diff.hunks)} lines")
    for j, hunk in enumerate(file_diff.hunks[:5]):  # Show first 5 lines
        print(f"    Hunk[{j}]: {repr(hunk)}")
    print()
