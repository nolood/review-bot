# Line Code Quick Reference

## What is line_code?

`line_code` is a GitLab-specific identifier for lines in a diff, required when posting inline comments to context lines (unchanged lines shown for reference in the diff).

## Format

```
{SHA1(file_path)}_{old_line}_{new_line}
```

## Examples

For file `src/example.py` (SHA1: `7cf3afab...`):

| Line Type | old_line | new_line | line_code | Required by GitLab? |
|-----------|----------|----------|-----------|---------------------|
| Added     | None     | 42       | `7cf3afab...__42` | No |
| Context   | 41       | 42       | `7cf3afab..._41_42` | **YES** |
| Modified  | 41       | 42       | `7cf3afab..._41_42` | **YES** |

## Usage in Code

### 1. Calculate line_code

```python
from src.line_code_mapper import calculate_line_code

# For a context line at line 42 (old line 41)
line_code = calculate_line_code("src/example.py", old_line=41, new_line=42)
# Result: 7cf3afab565662c615db7b22dca3f4ea4785f81a_41_42

# For an added line at line 42
line_code = calculate_line_code("src/example.py", old_line=None, new_line=42)
# Result: 7cf3afab565662c615db7b22dca3f4ea4785f81a__42
```

### 2. Get line info from validator

```python
from src.line_code_mapper import LinePositionValidator

validator = LinePositionValidator()
validator.build_mappings_from_diff_data(diff_data)

# Get complete line information
line_info = validator.get_line_info("src/example.py", 42)

# Access line_code
if line_info:
    print(f"Line code: {line_info.line_code}")
    print(f"Old line: {line_info.old_line}")
    print(f"Line type: {line_info.line_type}")
```

### 3. Post inline comment with line_code

```python
from src.gitlab_client import GitLabClient

client = GitLabClient()

# Post comment with line_code (for context lines)
client.post_inline_comment(
    body="This is a comment",
    file_path="src/example.py",
    line_number=42,
    base_sha="abc123...",
    start_sha="def456...",
    head_sha="ghi789...",
    old_line=41,           # Required for context lines
    line_code="7cf3afab..."  # Required for context lines
)
```

## When is line_code Required?

### Required (GitLab returns error without it):
- ✓ Context lines (unchanged lines in diff)
- ✓ Lines within modified regions

### Not Required (but included for consistency):
- ○ Purely added lines (new code)

### Cannot Comment:
- ✗ Removed lines (don't exist in new version)

## Error Messages

If you see:
```
GitLabAPIError: line_code can't be blank
```

This means:
1. You're trying to comment on a context line
2. The `line_code` field is missing from the position object
3. Solution: Ensure `old_line` and `line_code` are passed to `post_inline_comment()`

## Implementation Flow

```
1. Parse diff
   ↓
2. Extract line positions (line_code_mapper.py)
   - Calculate line_code for each line
   - Store in LinePositionInfo
   ↓
3. Validate comment position (comment_publisher.py)
   - Get LinePositionInfo from validator
   - Extract old_line and line_code
   ↓
4. Post to GitLab (gitlab_client.py)
   - Include old_line in position object
   - Include line_code in position object
```

## Testing

Run the test suite:
```bash
python3 test_line_code_implementation.py
python3 verify_line_code_integration.py
```

## Key Files

- `src/line_code_mapper.py` - Line code calculation and storage
- `src/gitlab_client.py` - GitLab API integration
- `src/comment_publisher.py` - Comment publishing logic

## References

- GitLab API Docs: [Discussions API](https://docs.gitlab.com/ee/api/discussions.html)
- Implementation: `LINE_CODE_IMPLEMENTATION.md`
