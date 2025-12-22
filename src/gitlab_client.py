"""
GitLab API client for the GLM Code Review Bot.

This module provides a comprehensive client for interacting with the GitLab API,
including fetching merge request diffs, posting comments, and handling errors.
"""

import os
import json
from typing import Dict, List, Optional, Any, Type
import requests

try:
    from src.config.settings import settings
    from src.utils.exceptions import GitLabAPIError
    from src.utils.logger import get_logger
    from src.utils.retry import api_retry
except ImportError:
    # Fallback for when running in test environment
    settings = None
    GitLabAPIError = Exception
    
    def get_logger(name: str):
        import logging
        return logging.getLogger(name)
    
    def api_retry(func):
        return func


class GitLabClient:
    """
    Client for interacting with the GitLab API.
    
    Provides methods for fetching merge request diffs,
    posting comments, and handling GitLab API responses.
    """
    
    def __init__(self):
        """Initialize the GitLab client with configuration settings."""
        self.logger = get_logger("gitlab_client")
        
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
        
        self.logger.info(
            "GitLab client initialized",
            extra={
                "api_url": self.api_url,
                "project_id": self.project_id,
                "mr_iid": self.mr_iid
            }
        )
    
    @api_retry
    def get_merge_request_diff(self) -> str:
        """
        Fetch the merge request diff from GitLab API.
        
        Returns:
            Formatted diff string for analysis
            
        Raises:
            GitLabAPIError: If diff retrieval fails
        """
        url = f"{self.api_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}/diffs"
        
        try:
            self.logger.debug(f"Fetching MR diff from {url}")
            
            response = requests.get(url, headers=self.headers)
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
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch merge request diff: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                }
            )
            # Create error details for logging
            error_details = {
                "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                "endpoint": url
            }
            self.logger.error(f"GitLab API error details: {error_details}")
            raise GitLabAPIError(error_msg)
    
    @api_retry
    def post_comment(self, body: str, position: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Post a comment to the merge request.
        
        Args:
            body: Comment body text
            position: Optional position data for inline comments
            
        Returns:
            API response data for the created comment
            
        Raises:
            GitLabAPIError: If comment posting fails
        """
        url = f"{self.api_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}/notes"
        
        payload = {"body": body}
        if position:
            payload = {"body": body, "position": position}
        
        try:
            self.logger.debug(
                "Posting comment to MR",
                extra={
                    "url": url,
                    "has_position": position is not None,
                    "body_length": len(body)
                }
            )
            
            response = requests.post(url, json=payload, headers=self.headers)
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
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to post comment: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None,
                    "is_inline": position is not None
                }
            )
            raise GitLabAPIError(error_msg)
    
    def post_inline_comment(
        self,
        body: str,
        file_path: str,
        line_number: int,
        base_sha: str,
        start_sha: str,
        head_sha: str
    ) -> Dict[str, Any]:
        """
        Post an inline comment to a specific line in a file.
        
        Args:
            body: Comment body text
            file_path: Path to the file being commented on
            line_number: Line number for the comment
            base_sha: Base SHA of the merge request
            start_sha: Start SHA of the merge request
            head_sha: Head SHA of the merge request
            
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
            "new_path": file_path,
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
        
        return self.post_comment(body, position)
    
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
    
    def get_merge_request_details(self) -> Dict[str, Any]:
        """
        Fetch detailed information about the merge request.
        
        Returns:
            Merge request details including SHAs and metadata
            
        Raises:
            GitLabAPIError: If MR details retrieval fails
        """
        url = f"{self.api_url}/projects/{self.project_id}/merge_requests/{self.mr_iid}"
        
        try:
            self.logger.debug(f"Fetching MR details from {url}")
            
            response = requests.get(url, headers=self.headers)
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
            
        except requests.exceptions.RequestException as e:
            error_msg = f"Failed to fetch merge request details: {str(e)}"
            self.logger.error(
                error_msg,
                extra={
                    "url": url,
                    "error_type": type(e).__name__,
                    "status_code": getattr(e.response, 'status_code', None) if hasattr(e, 'response') else None
                }
            )
            raise GitLabAPIError(error_msg)