"""
Async GitLab API client for the GLM Code Review Bot.

This module provides a comprehensive async client for interacting with the GitLab API,
including fetching merge request diffs, posting comments, and handling errors.
"""

import os
import json
from typing import Dict, List, Optional, Any, Type
from contextlib import asynccontextmanager

import httpx
import asyncio

try:
    from src.config.settings import settings
    from src.utils.exceptions import GitLabAPIError
    from src.utils.logger import get_logger
    from src.utils.retry import api_retry
except ImportError:
    # Fallback for when running in test environment
    settings = None
    GitLabAPIError = Exception
    api_retry = lambda func: func
    # Use centralized fallback logger
    from src.utils.logger import get_fallback_logger as get_logger


class AsyncGitLabClient:
    """
    Async client for interacting with the GitLab API.
    
    Provides async methods for fetching merge request diffs,
    posting comments, and handling GitLab API responses.
    """
    
    def __init__(self, timeout: int = 60, limits: Optional[httpx.Limits] = None):
        """
        Initialize the async GitLab client with configuration settings.
        
        Args:
            timeout: Request timeout in seconds
            limits: Connection limits for HTTP client
        """
        self.logger = get_logger("async_gitlab_client")
        self.timeout = timeout
        
        # Get configuration from settings or environment
        if settings:
            self.token = settings.gitlab_token
            self.api_url = settings.gitlab_api_url
            self.project_id = settings.project_id
            self.mr_iid = settings.mr_iid
        else:
            self.token = os.getenv("GITLAB_TOKEN", "")
            self.api_url = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4")
            self.project_id = os.getenv("CI_PROJECT_ID", "")
            self.mr_iid = os.getenv("CI_MERGE_REQUEST_IID", "")
        
        # Validate required configuration
        if not self.token:
            raise GitLabAPIError("GitLab token is required")
        
        # Prepare headers for API requests
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
        
        # HTTP client limits
        self.limits = limits or httpx.Limits(
            max_keepalive_connections=10,
            max_connections=20
        )
        
        self.logger.info(
            "Async GitLab client initialized",
            extra={
                "api_url": self.api_url,
                "project_id": self.project_id,
                "mr_iid": self.mr_iid,
                "timeout": timeout
            }
        )
    
    @asynccontextmanager
    async def get_client(self):
        """Async context manager for HTTP client."""
        async with httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
            headers=self.headers
        ) as client:
            yield client
    
    async def __aenter__(self):
        """Async context manager entry."""
        self._client = httpx.AsyncClient(
            timeout=self.timeout,
            limits=self.limits,
            headers=self.headers
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self._client.aclose()
    
    async def get_merge_request_diff(
        self,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> str:
        """
        Async fetch the merge request diff from GitLab API.

        Args:
            project_id: Project ID (uses default if not provided)
            mr_iid: MR IID (uses default if not provided)

        Returns:
            Formatted diff string for analysis

        Raises:
            GitLabAPIError: If diff retrieval fails
        """
        pid = project_id or self.project_id
        iid = mr_iid or self.mr_iid
        url = f"{self.api_url}/projects/{pid}/merge_requests/{iid}/diffs"
        
        try:
            self.logger.debug(f"Fetching MR diff from {url}")
            
            async with self.get_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                diffs = response.json()
                formatted_diff = self._format_diff(diffs)
                
                self.logger.info(
                    "Successfully retrieved MR diff",
                    extra={
                        "files_count": len(diffs) if diffs else 0,
                        "diff_size": len(formatted_diff)
                    }
                )
                
                return formatted_diff
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to fetch merge request diff: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "status_code": e.response.status_code if e.response else None
                }
            )
            error_details = {
                "status_code": e.response.status_code if e.response else None,
                "endpoint": url
            }
            self.logger.error(f"GitLab API error details: {error_details}")
            raise GitLabAPIError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Failed to fetch merge request diff: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__
                }
            )
            raise GitLabAPIError(error_msg)

    async def get_merge_request_diffs_raw(
        self,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Async fetch raw merge request diffs from GitLab API.

        Args:
            project_id: Optional project ID override (uses self.project_id if not provided)
            mr_iid: Optional MR IID override (uses self.mr_iid if not provided)

        Returns:
            List of raw diff objects from GitLab API

        Raises:
            GitLabAPIError: If diff retrieval fails
        """
        pid = project_id or self.project_id
        iid = mr_iid or self.mr_iid
        url = f"{self.api_url}/projects/{pid}/merge_requests/{iid}/diffs"

        try:
            self.logger.debug(f"Fetching raw MR diffs from {url}")

            async with self.get_client() as client:
                response = await client.get(url)
                response.raise_for_status()

                diffs = response.json()

                self.logger.info(
                    "Successfully retrieved raw MR diffs",
                    extra={
                        "files_count": len(diffs) if diffs else 0
                    }
                )

                # Debug: log structure of first diff entry
                if diffs and len(diffs) > 0:
                    first_diff = diffs[0]
                    self.logger.debug(
                        "First diff entry structure",
                        extra={
                            "keys": list(first_diff.keys()),
                            "old_path": first_diff.get("old_path"),
                            "new_path": first_diff.get("new_path"),
                            "has_diff": "diff" in first_diff
                        }
                    )

                return diffs

        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to fetch raw merge request diffs: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "status_code": e.response.status_code if e.response else None
                }
            )
            raise GitLabAPIError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Failed to fetch raw merge request diffs: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__
                }
            )
            raise GitLabAPIError(error_msg)

    async def post_comment(
        self,
        body: str,
        position: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async post a comment to the merge request.

        Args:
            body: Comment body text
            position: Optional position data for inline comments
            project_id: Optional project ID override (uses self.project_id if not provided)
            mr_iid: Optional MR IID override (uses self.mr_iid if not provided)

        Returns:
            API response data for the created comment

        Raises:
            GitLabAPIError: If comment posting fails
        """
        # Validate position structure if provided
        if position:
            required_fields = ["base_sha", "start_sha", "head_sha", "position_type", "new_path", "new_line"]
            missing_fields = [field for field in required_fields if field not in position]

            if missing_fields:
                error_msg = f"Invalid position object: missing required fields {missing_fields}"
                self.logger.error(
                    error_msg,
                    extra={
                        "position": position,
                        "missing_fields": missing_fields
                    }
                )
                raise GitLabAPIError(error_msg)

        # Use provided IDs or fall back to instance defaults
        pid = project_id or self.project_id
        iid = mr_iid or self.mr_iid

        # Use discussions endpoint for inline comments (with position)
        # Use notes endpoint for general MR comments (without position)
        if position:
            url = f"{self.api_url}/projects/{pid}/merge_requests/{iid}/discussions"
            payload = {"body": body, "position": position}
        else:
            url = f"{self.api_url}/projects/{pid}/merge_requests/{iid}/notes"
            payload = {"body": body}
        
        try:
            self.logger.debug(
                "Posting comment to MR",
                extra={
                    "url": url,
                    "has_position": position is not None,
                    "body_length": len(body)
                }
            )
            
            async with self.get_client() as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                
                self.logger.info(
                    "Successfully posted comment",
                    extra={
                        "comment_id": result.get("id"),
                        "is_inline": position is not None
                    }
                )
                
                return result
            
        except httpx.HTTPStatusError as e:
            # Extract error details from response body
            error_details = ""
            try:
                if e.response is not None:
                    error_details = e.response.text
            except:
                pass

            # Include error_details in the exception message for proper error handling
            error_msg = f"Failed to post comment: {str(e)}"
            if error_details:
                error_msg = f"{error_msg} - Details: {error_details}"

            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "status_code": e.response.status_code if e.response else None,
                    "is_inline": position is not None,
                    "error_details": error_details,
                    "position": position if position else None
                }
            )
            raise GitLabAPIError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Failed to post comment: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "is_inline": position is not None
                }
            )
            raise GitLabAPIError(error_msg)
    
    async def post_inline_comment(
        self,
        body: str,
        file_path: str,
        line_number: int,
        base_sha: str,
        start_sha: str,
        head_sha: str,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async post an inline comment to a specific line in a file.

        Args:
            body: Comment body text
            file_path: Path to the file being commented on
            line_number: Line number for the comment
            base_sha: Base SHA of the merge request
            start_sha: Start SHA of the merge request
            head_sha: Head SHA of the merge request
            project_id: Optional project ID override (uses self.project_id if not provided)
            mr_iid: Optional MR IID override (uses self.mr_iid if not provided)

        Returns:
            API response data for the created comment

        Raises:
            GitLabAPIError: If inline comment posting fails
        """
        position = {
            "base_sha": base_sha,
            "start_sha": start_sha,
            "head_sha": head_sha,
            "position_type": "text",
            "old_path": file_path,  # Required by GitLab API
            "new_path": file_path,
            "old_line": None,  # Comment on new line only
            "new_line": line_number
        }

        self.logger.debug(
            "Posting inline comment",
            extra={
                "file_path": file_path,
                "line_number": line_number,
                "body_length": len(body)
            }
        )

        return await self.post_comment(body, position, project_id, mr_iid)
    
    async def get_merge_request_details(
        self,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Async fetch detailed information about the merge request.

        Args:
            project_id: Optional project ID override (uses self.project_id if not provided)
            mr_iid: Optional MR IID override (uses self.mr_iid if not provided)

        Returns:
            Merge request details including SHAs and metadata

        Raises:
            GitLabAPIError: If MR details retrieval fails
        """
        pid = project_id or self.project_id
        iid = mr_iid or self.mr_iid
        url = f"{self.api_url}/projects/{pid}/merge_requests/{iid}"
        
        try:
            self.logger.debug(f"Fetching MR details from {url}")
            
            async with self.get_client() as client:
                response = await client.get(url)
                response.raise_for_status()
                
                mr_details = response.json()
                
                self.logger.info(
                    "Successfully retrieved MR details",
                    extra={
                        "mr_title": mr_details.get("title"),
                        "source_branch": mr_details.get("source_branch"),
                        "target_branch": mr_details.get("target_branch"),
                        "author": mr_details.get("author", {}).get("name") if mr_details.get("author") else None
                    }
                )
                
                return mr_details
            
        except httpx.HTTPStatusError as e:
            error_msg = f"Failed to fetch merge request details: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "status_code": e.response.status_code if e.response else None
                }
            )
            raise GitLabAPIError(error_msg)
        except httpx.RequestError as e:
            error_msg = f"Failed to fetch merge request details: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__
                }
            )
            raise GitLabAPIError(error_msg)
    
    async def post_multiple_comments(
        self, 
        comments: List[Dict[str, Any]], 
        concurrent_limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Post multiple comments concurrently with rate limiting.
        
        Args:
            comments: List of comment dictionaries with body and optional position
            concurrent_limit: Maximum number of concurrent requests
            
        Returns:
            List of API response data for created comments
            
        Raises:
            GitLabAPIError: If any comment posting fails
        """
        if not comments:
            return []
        
        self.logger.info(f"Posting {len(comments)} comments concurrently")
        
        semaphore = asyncio.Semaphore(concurrent_limit)
        
        async def post_single_comment(comment_data: Dict[str, Any]) -> Dict[str, Any]:
            async with semaphore:
                try:
                    body = comment_data.get("body", "")
                    position = comment_data.get("position")
                    return await self.post_comment(body, position)
                except Exception as e:
                    self.logger.error(f"Failed to post comment: {e}")
                    raise
        
        try:
            results = await asyncio.gather(
                *[post_single_comment(comment) for comment in comments],
                return_exceptions=False
            )
            
            self.logger.info(f"Successfully posted {len(results)} comments")
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to post multiple comments: {e}")
            raise GitLabAPIError(f"Failed to post comments: {e}") from e
    
    def _format_diff(self, diffs: List[Dict[str, Any]]) -> str:
        """
        Format GitLab diff response into a unified diff format.
        
        Args:
            diffs: List of diff objects from GitLab API
            
        Returns:
            Formatted diff string suitable for analysis
        """
        if not diffs:
            return ""
        
        formatted_parts = []
        
        for diff_data in diffs:
            old_path = diff_data.get("old_path", "")
            new_path = diff_data.get("new_path", "")
            diff_content = diff_data.get("diff", "")
            
            # Add file headers
            formatted_parts.append(f"--- {old_path}")
            formatted_parts.append(f"+++ {new_path}")
            formatted_parts.append(diff_content)
        
        return "\n".join(formatted_parts)


# Maintain backward compatibility with synchronous interface
class GitLabClient:
    """
    Synchronous GitLab client for backward compatibility.
    
    This class provides the same interface as the async client but
    executes async operations in a sync context.
    """
    
    def __init__(self, timeout: int = 60, limits: Optional[httpx.Limits] = None):
        self._async_client = AsyncGitLabClient(timeout, limits)
        self.logger = get_logger("gitlab_client")
    
    def get_merge_request_diff(
        self,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> str:
        """Synchronous wrapper for async method."""
        return asyncio.run(self._async_client.get_merge_request_diff(project_id, mr_iid))

    def get_merge_request_diffs_raw(
        self,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> list[dict[str, Any]]:
        """
        Fetch raw merge request diffs from GitLab API.

        Args:
            project_id: Project ID (uses default if not provided)
            mr_iid: MR IID (uses default if not provided)

        Returns:
            List of raw diff objects from GitLab API

        Raises:
            GitLabAPIError: If diff retrieval fails
        """
        return asyncio.run(self._async_client.get_merge_request_diffs_raw(project_id, mr_iid))

    def post_comment(
        self,
        body: str,
        position: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async method."""
        return asyncio.run(self._async_client.post_comment(body, position, project_id, mr_iid))

    def get_merge_request_details(
        self,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async method."""
        return asyncio.run(self._async_client.get_merge_request_details(project_id, mr_iid))

    def post_inline_comment(
        self,
        body: str,
        file_path: str,
        line_number: int,
        base_sha: str,
        start_sha: str,
        head_sha: str,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """Synchronous wrapper for async method."""
        return asyncio.run(self._async_client.post_inline_comment(
            body, file_path, line_number, base_sha, start_sha, head_sha, project_id, mr_iid
        ))
    
    def _format_diff(self, diffs: List[Dict[str, Any]]) -> str:
        """Delegate to async client."""
        return self._async_client._format_diff(diffs)