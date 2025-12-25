"""
Test script to verify critical fixes for GitLab client.

This script tests:
1. Position structure includes old_path and old_line
2. Position validation works correctly
3. Discussions endpoint is used for positioned comments
"""

import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from unittest.mock import Mock, patch, AsyncMock
import pytest
import asyncio


def test_async_position_structure():
    """Verify async version includes old_path and old_line in position object."""
    from gitlab_client_async import AsyncGitLabClient

    # Create mock environment
    with patch.dict(os.environ, {
        'GITLAB_TOKEN': 'test_token',
        'GITLAB_API_URL': 'https://gitlab.example.com/api/v4',
        'CI_PROJECT_ID': '123',
        'CI_MERGE_REQUEST_IID': '456'
    }):
        client = AsyncGitLabClient()

        # Create position object using post_inline_comment method
        # This will create the position dict internally
        async def check_position():
            with patch.object(client, 'post_comment', new_callable=AsyncMock) as mock_post:
                mock_post.return_value = {"id": 1, "body": "test"}

                await client.post_inline_comment(
                    body="Test comment",
                    file_path="src/test.py",
                    line_number=42,
                    base_sha="abc123",
                    start_sha="def456",
                    head_sha="ghi789"
                )

                # Check that post_comment was called with correct position
                assert mock_post.call_count == 1
                call_args = mock_post.call_args
                # Position is passed as second positional argument
                position = call_args[0][1]  # (body, position)

                # Verify all required fields are present
                assert 'old_path' in position, "Missing old_path in position"
                assert 'new_path' in position, "Missing new_path in position"
                assert 'old_line' in position, "Missing old_line in position"
                assert 'new_line' in position, "Missing new_line in position"
                assert position['old_path'] == "src/test.py"
                assert position['new_path'] == "src/test.py"
                assert position['old_line'] is None
                assert position['new_line'] == 42

                print("✓ Async position structure includes old_path and old_line")

        asyncio.run(check_position())


def test_async_position_validation():
    """Verify async version validates position structure."""
    from gitlab_client_async import AsyncGitLabClient

    with patch.dict(os.environ, {
        'GITLAB_TOKEN': 'test_token',
        'GITLAB_API_URL': 'https://gitlab.example.com/api/v4',
        'CI_PROJECT_ID': '123',
        'CI_MERGE_REQUEST_IID': '456'
    }):
        client = AsyncGitLabClient()

        async def check_validation():
            # Test with invalid position (missing required fields)
            invalid_position = {
                "base_sha": "abc123",
                "new_path": "test.py"
                # Missing: start_sha, head_sha, position_type, new_line
            }

            try:
                await client.post_comment("Test", invalid_position)
                assert False, "Should have raised exception for invalid position"
            except Exception as e:
                # Either GitLabAPIError or generic Exception depending on fallback
                assert "missing required fields" in str(e)
                print("✓ Async position validation works correctly")

        asyncio.run(check_validation())


def test_discussions_endpoint_used():
    """Verify discussions endpoint is used when position is provided."""
    from gitlab_client_async import AsyncGitLabClient

    with patch.dict(os.environ, {
        'GITLAB_TOKEN': 'test_token',
        'GITLAB_API_URL': 'https://gitlab.example.com/api/v4',
        'CI_PROJECT_ID': '123',
        'CI_MERGE_REQUEST_IID': '456'
    }):
        client = AsyncGitLabClient()

        async def check_endpoint():
            valid_position = {
                "base_sha": "abc123",
                "start_sha": "def456",
                "head_sha": "ghi789",
                "position_type": "text",
                "old_path": "test.py",
                "new_path": "test.py",
                "old_line": None,
                "new_line": 42
            }

            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.json.return_value = {"id": 1, "body": "Test"}
                mock_response.raise_for_status = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = AsyncMock()
                mock_client_class.return_value = mock_client

                await client.post_comment("Test comment", valid_position)

                # Check that post was called with discussions endpoint
                call_args = mock_client.post.call_args
                url = call_args[0][0]
                assert url.endswith('/discussions'), f"Expected /discussions endpoint, got {url}"
                print("✓ Discussions endpoint used for positioned comments")

        asyncio.run(check_endpoint())


def test_notes_endpoint_without_position():
    """Verify notes endpoint is used when position is None."""
    from gitlab_client_async import AsyncGitLabClient

    with patch.dict(os.environ, {
        'GITLAB_TOKEN': 'test_token',
        'GITLAB_API_URL': 'https://gitlab.example.com/api/v4',
        'CI_PROJECT_ID': '123',
        'CI_MERGE_REQUEST_IID': '456'
    }):
        client = AsyncGitLabClient()

        async def check_endpoint():
            with patch('httpx.AsyncClient') as mock_client_class:
                mock_client = AsyncMock()
                mock_response = AsyncMock()
                mock_response.json.return_value = {"id": 1, "body": "Test"}
                mock_response.raise_for_status = AsyncMock()
                mock_client.post.return_value = mock_response
                mock_client.__aenter__.return_value = mock_client
                mock_client.__aexit__.return_value = AsyncMock()
                mock_client_class.return_value = mock_client

                await client.post_comment("Test comment", None)

                # Check that post was called with notes endpoint
                call_args = mock_client.post.call_args
                url = call_args[0][0]
                assert url.endswith('/notes'), f"Expected /notes endpoint, got {url}"
                print("✓ Notes endpoint used for comments without position")

        asyncio.run(check_endpoint())


if __name__ == "__main__":
    print("\n" + "="*70)
    print("Testing Critical Fixes for GitLab Client")
    print("="*70 + "\n")

    try:
        test_async_position_structure()
        test_async_position_validation()
        test_discussions_endpoint_used()
        test_notes_endpoint_without_position()

        print("\n" + "="*70)
        print("All critical fixes verified successfully!")
        print("="*70 + "\n")
        sys.exit(0)
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
