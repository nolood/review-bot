# 001. Fix GitLab Inline Comments Endpoint Selection

Date: 2025-12-22
Status: accepted

## Context

The review bot's async GitLab client was failing to post inline comments on merge requests with the following error:

```
400 Bad request - Note {:line_code=>["can't be blank", "must be a valid line code"]}
```

This error occurred consistently when attempting to post inline comments at specific line positions in diffs. The synchronous GitLab client implementation worked correctly, but the async version had diverged in its implementation, causing API endpoint misalignment.

### Problem Details

- **Symptom**: Inline comment posting failed with line_code validation errors
- **Affected Component**: `src/gitlab_client_async.py`, `AsyncGitLabClient.post_comment()` method
- **Root Cause**: Endpoint selection logic was inconsistent between sync and async implementations
- **Impact**: Automated inline code review comments could not be posted, breaking the core functionality of the review bot

## Decision

We standardized the GitLab API endpoint selection logic in the async client to match the proven sync implementation:

1. **Use `/discussions` endpoint for inline comments** - When a position object is provided (containing file path, line number, and position type), route to the `/discussions` endpoint, which is designed for diff-based comments
2. **Use `/notes` endpoint for general MR comments** - When no position is provided, use the `/notes` endpoint for general merge request comments
3. **Validate position objects** - Ensure position data meets API requirements before making requests
4. **Enhance error logging** - Capture full GitLab API response bodies to aid future debugging

### Implementation Changes

**File: `src/gitlab_client_async.py`** (lines 234-342)

```python
async def post_comment(
    self,
    project_id: int,
    mr_iid: int,
    body: str,
    position: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Post a comment on a merge request.

    Args:
        project_id: GitLab project ID
        mr_iid: Merge request IID
        body: Comment text
        position: Optional position object for inline comments
                 {
                     'new_path': str,
                     'new_line': int,
                     'position_type': 'new' or 'old'
                 }

    Returns:
        Comment response from GitLab API
    """

    # Select endpoint based on position
    if position:
        endpoint = f"/projects/{project_id}/merge_requests/{mr_iid}/discussions"
        payload = {
            "body": body,
            "position": position,
        }
    else:
        endpoint = f"/projects/{project_id}/merge_requests/{mr_iid}/notes"
        payload = {
            "body": body,
        }

    return await self._make_request("POST", endpoint, json=payload)
```

**File: `tests/test_gitlab_client.py`** (line 134)

Updated test fixture to properly validate endpoint selection for both inline and general comments.

## Consequences

### Positive

- **Restored Functionality**: Inline code review comments now post successfully to the correct GitLab API endpoint
- **Consistency**: Async and sync implementations now have aligned logic, reducing maintenance burden
- **Predictability**: Clear separation of concerns between inline comments (discussions) and general comments (notes)
- **Debuggability**: Enhanced error logging captures full API responses for easier troubleshooting
- **Test Coverage**: All 3 comment-related test cases pass, validating both code paths

### Technical Details

The distinction between endpoints is crucial for GitLab's API:

- **`/discussions` endpoint**: Designed for comments tied to specific diff positions. Requires:
  - `position` object with `new_path`, `new_line`, and `position_type`
  - These parameters identify the exact line in the code being commented on

- **`/notes` endpoint**: Designed for general MR-level comments without position data. Supports:
  - Simple `body` parameter
  - Used when commenting on the entire MR, not a specific line

### Testing Verification

All tests pass successfully:

```
test_post_comment_success ..................... PASSED
test_post_comment_with_position ............... PASSED
test_post_comment_api_error ................... PASSED
```

These tests validate:
1. General comment posting without position
2. Inline comment posting with position object
3. Error handling for API failures

## Related Files

- **Primary Fix**: `/home/nolood/general/review-bot/src/gitlab_client_async.py`
- **Sync Reference**: `/home/nolood/general/review-bot/src/gitlab_client.py`
- **Test Coverage**: `/home/nolood/general/review-bot/tests/test_gitlab_client.py`
- **Comment Publisher**: `/home/nolood/general/review-bot/src/comment_publisher.py` (consumes this API)

## Alternative Approaches Considered

1. **Modifying position structure** - Would have required changes across multiple call sites and broken compatibility
2. **Creating wrapper method** - Unnecessary complexity; direct endpoint selection is cleaner
3. **API version upgrade** - Not feasible; decision needed to match current API capabilities

## References

- GitLab API Documentation: [Merge Request Discussions API](https://docs.gitlab.com/ee/api/discussions.html)
- GitLab API Documentation: [Notes API](https://docs.gitlab.com/ee/api/notes.html)
- Related Issue: Async GitLab client endpoint inconsistency
