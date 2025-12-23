# Line Code Implementation Flow Diagram

## Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitLab Merge Request                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ Diff Data (from GitLab API)                                      │   │
│  │ {                                                                 │   │
│  │   "old_path": "src/example.py",                                   │   │
│  │   "new_path": "src/example.py",                                   │   │
│  │   "diff": "@@ -10,5 +10,6 @@ def example():\n..."               │   │
│  │ }                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    Step 1: Parse Diff & Extract Lines                    │
│                      (LinePositionValidator)                             │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ _extract_valid_lines_from_diff()                                 │   │
│  │                                                                   │   │
│  │ For each line in diff:                                            │   │
│  │   - Parse hunk header: @@ -10,5 +10,6 @@                         │   │
│  │   - Track old_line and new_line counters                         │   │
│  │   - Identify line type (added/context/removed)                   │   │
│  │   - Calculate line_code = SHA1(file)_old_new                     │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                    Step 2: Store Line Information                        │
│                        (FileLineMapping)                                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ LinePositionInfo {                                                │   │
│  │   file_path: "src/example.py"                                     │   │
│  │   line_number: 12          ← New line number                      │   │
│  │   old_line: 11             ← Old line number (or None)            │   │
│  │   line_type: "context"     ← added/context/removed                │   │
│  │   in_diff_hunk: true                                              │   │
│  │   line_code: "7cf3afab..._11_12"  ← SHA1(file)_old_new           │   │
│  │ }                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                Step 3: AI Analysis & Comment Generation                  │
│                         (GLM API Response)                               │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ {                                                                 │   │
│  │   "file": "src/example.py",                                       │   │
│  │   "line": 12,                                                     │   │
│  │   "message": "Consider using a constant here",                   │   │
│  │   "severity": "medium"                                            │   │
│  │ }                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│              Step 4: Validate Position & Retrieve Line Info              │
│                      (CommentPublisher)                                  │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ 1. Check if line is valid for inline comments                    │   │
│  │    → is_valid_position("src/example.py", 12)                     │   │
│  │                                                                   │   │
│  │ 2. Get detailed line information                                 │   │
│  │    → line_info = get_line_info("src/example.py", 12)            │   │
│  │                                                                   │   │
│  │ 3. Extract old_line and line_code                                │   │
│  │    → old_line = line_info.old_line      # 11                     │   │
│  │    → line_code = line_info.line_code    # "7cf3afab..._11_12"   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                Step 5: Post Inline Comment to GitLab                     │
│                         (GitLabClient)                                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ post_inline_comment(                                              │   │
│  │   body="Consider using a constant here",                         │   │
│  │   file_path="src/example.py",                                     │   │
│  │   line_number=12,                                                 │   │
│  │   base_sha="abc123...",                                           │   │
│  │   start_sha="def456...",                                          │   │
│  │   head_sha="ghi789...",                                           │   │
│  │   old_line=11,              ← From LinePositionInfo               │   │
│  │   line_code="7cf3afab..."   ← From LinePositionInfo               │   │
│  │ )                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                Step 6: GitLab API Position Object                        │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ position = {                                                      │   │
│  │   "base_sha": "abc123...",                                        │   │
│  │   "start_sha": "def456...",                                       │   │
│  │   "head_sha": "ghi789...",                                        │   │
│  │   "position_type": "text",                                        │   │
│  │   "old_path": "src/example.py",                                   │   │
│  │   "new_path": "src/example.py",                                   │   │
│  │   "old_line": 11,           ← Required for context lines          │   │
│  │   "new_line": 12,                                                 │   │
│  │   "line_code": "7cf3afab565662c615db7b22dca3f4ea4785f81a_11_12"  │   │
│  │                             ↑ Required for context lines          │   │
│  │ }                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ↓
┌─────────────────────────────────────────────────────────────────────────┐
│                         GitLab API Response                              │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │ ✅ SUCCESS: Inline comment posted                                │   │
│  │ {                                                                 │   │
│  │   "id": 12345,                                                    │   │
│  │   "type": "DiffNote",                                             │   │
│  │   "body": "Consider using a constant here",                      │   │
│  │   "position": { ... }                                             │   │
│  │ }                                                                 │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

## Key Decision Points

### Line Type Determines Requirements

```
┌──────────────┬──────────┬──────────┬──────────────┬─────────────────┐
│  Line Type   │ old_line │ new_line │  line_code   │  GitLab Requires│
├──────────────┼──────────┼──────────┼──────────────┼─────────────────┤
│ Added        │   None   │   42     │  sha__42     │  Optional       │
│ Context      │   41     │   42     │  sha_41_42   │  REQUIRED ✓     │
│ Modified     │   41     │   42     │  sha_41_42   │  REQUIRED ✓     │
│ Removed      │   41     │   None   │  sha_41_     │  Can't comment  │
└──────────────┴──────────┴──────────┴──────────────┴─────────────────┘
```

### Error Handling Flow

```
Comment Request
      │
      ↓
Validate Position ──────→ Invalid? ──────→ Post as general comment
      │                                     with note
      │
      ↓ Valid
Get Line Info
      │
      ↓
Extract old_line & line_code
      │
      ↓
Check SHAs available? ───→ Missing? ──────→ Post as general comment
      │                                      with note
      │
      ↓ All present
Post Inline Comment
      │
      ↓
Success? ────────────────→ Error? ─────────→ Check error type
      │                                            │
      ↓                                            ↓
✅ Done                              line_code error? ────→ Fallback
                                              │
                                              ↓ Other
                                          Propagate error
```

## Line Code Calculation Detail

```
Input:
  file_path = "src/config/settings.py"
  old_line = 12
  new_line = 13

Step 1: Calculate SHA1 of file path
  ┌─────────────────────────────────────────────┐
  │ SHA1("src/config/settings.py")              │
  │   = "98a1789c41d06dedb97232d7e2b0036c69..."  │
  └─────────────────────────────────────────────┘

Step 2: Format with line numbers
  ┌─────────────────────────────────────────────┐
  │ old_str = "12"  (or "" if None)             │
  │ new_str = "13"  (or "" if None)             │
  └─────────────────────────────────────────────┘

Step 3: Concatenate with underscores
  ┌─────────────────────────────────────────────┐
  │ line_code = "98a1789c..._12_13"             │
  └─────────────────────────────────────────────┘

Output:
  "98a1789c41d06dedb97232d7e2b0036c69eb92d5_12_13"
   └────────────┬────────────┘                ↑  ↑
           file SHA1                        old new
```

## Integration Points

```
┌─────────────────────────────────────────────────────────────┐
│                    review_bot.py (main)                      │
│                                                               │
│  1. Fetch MR diff data from GitLab                           │
│  2. Build line position mappings (includes line_code)        │
│  3. Get AI review from GLM                                   │
│  4. Publish comments (uses line_code for context lines)      │
└─────────────────────────────────────────────────────────────┘
         │                │                │                │
         ↓                ↓                ↓                ↓
  ┌───────────┐  ┌──────────────┐  ┌─────────┐  ┌─────────────┐
  │  GitLab   │  │   Line Code  │  │   GLM   │  │  Comment    │
  │  Client   │  │   Mapper     │  │  Client │  │  Publisher  │
  └───────────┘  └──────────────┘  └─────────┘  └─────────────┘
       │                 │                            │
       │                 │                            │
       └─────────────────┴────────────────────────────┘
                         │
                         ↓
              All use line_code for
              proper inline commenting
```

## Benefits of This Implementation

1. **Early Calculation**: Line code calculated during diff parsing
2. **Single Source of Truth**: Stored in LinePositionInfo
3. **Automatic**: No manual calculation needed by callers
4. **Type-Safe**: Optional parameters maintain backward compatibility
5. **Debuggable**: Full logging at each step
6. **Testable**: Separated concerns enable unit testing
7. **Maintainable**: Clear data flow and responsibilities
