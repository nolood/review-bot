"""
Comment Publisher for the GLM Code Review Bot.

This module handles formatting and publishing of code review comments
to GitLab merge requests, including inline comments and summary reports.
"""

import time
import json
from typing import Dict, List, Optional, Any, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

try:
    from .gitlab_client import GitLabClient
    from .config.settings import settings
    from .utils.logger import get_logger
    from .utils.exceptions import CommentPublishError
    from .line_code_mapper import LinePositionValidator
except ImportError:
    # Fallback for direct imports
    from gitlab_client import GitLabClient
    try:
        from config.settings import settings
    except ImportError:
        settings = None
    from utils.logger import get_logger
    from utils.exceptions import CommentPublishError
    from line_code_mapper import LinePositionValidator



class CommentType(Enum):
    """Types of comments that can be published."""
    ISSUE = "issue"
    SUGGESTION = "suggestion"
    PRAISE = "praise"
    QUESTION = "question"
    SUMMARY = "summary"


class SeverityLevel(Enum):
    """Severity levels for code review feedback."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class FormattedComment:
    """Structured comment ready for publishing."""
    comment_type: CommentType
    severity: SeverityLevel
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    title: str = ""
    body: str = ""
    suggestion: Optional[str] = None
    code_snippet: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommentBatch:
    """Batch of comments for efficient publishing."""
    summary_comment: Optional[str] = None
    file_comments: List[FormattedComment] = field(default_factory=list)
    inline_comments: List[FormattedComment] = field(default_factory=list)


class CommentPublisher:
    """
    Handles formatting and publishing of code review comments.
    
    Transforms GLM API responses into structured GitLab comments with
    proper formatting, severity indicators, and rate limiting.
    """
    
    SEVERITY_EMOJIS = {
        SeverityLevel.LOW: "💡",
        SeverityLevel.MEDIUM: "⚠️",
        SeverityLevel.HIGH: "🔴",
        SeverityLevel.CRITICAL: "🚨"
    }
    
    COMMENT_TYPE_EMOJIS = {
        CommentType.ISSUE: "🐛",
        CommentType.SUGGESTION: "💭",
        CommentType.PRAISE: "👏",
        CommentType.QUESTION: "❓",
        CommentType.SUMMARY: "📋"
    }
    
    def __init__(
        self,
        gitlab_client: Optional[GitLabClient] = None,
        line_position_validator: Optional[LinePositionValidator] = None
    ):
        """
        Initialize the comment publisher.

        Args:
            gitlab_client: Optional pre-initialized GitLab client
            line_position_validator: Optional line position validator for validating inline comment positions
        """
        self.logger = get_logger("comment_publisher")
        self.gitlab_client = gitlab_client or GitLabClient()
        self.line_position_validator = line_position_validator

        # Rate limiting configuration
        self.last_comment_time = 0.0
        self.comment_delay = getattr(settings, 'api_request_delay', 0.5) if settings else 0.5
        self.max_batch_size = 10

        self.logger.info("Comment publisher initialized")
    
    def format_comments(self, glm_response: Union[str, Dict[str, Any]]) -> CommentBatch:
        """
        Transform GLM response into structured comments.
        
        Args:
            glm_response: Raw response from GLM API (JSON string or dict)
            
        Returns:
            CommentBatch with formatted comments
            
        Raises:
            CommentPublisherError: If response parsing fails
        """
        try:
            # Parse JSON response if needed
            if isinstance(glm_response, str):
                response_data = json.loads(glm_response)
            else:
                response_data = glm_response
            
            # Extract comments based on response structure
            comments = self._extract_comments_from_response(response_data)
            
            # Group comments by type and format them
            comment_batch = self._group_and_format_comments(comments)
            
            self.logger.info(
                "Formatted comments from GLM response",
                extra={
                    "total_comments": len(comments),
                    "file_comments": len(comment_batch.file_comments),
                    "inline_comments": len(comment_batch.inline_comments),
                    "has_summary": comment_batch.summary_comment is not None
                }
            )
            
            return comment_batch
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.error(f"Failed to parse GLM response: {e}")
            raise CommentPublishError(f"Invalid GLM response format: {e}")
    
    def publish_review_summary(
        self,
        summary: str,
        mr_details: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish overall MR summary comment.

        Args:
            summary: Summary text to publish
            mr_details: Optional MR details for context
            project_id: Optional project ID for GitLab API
            mr_iid: Optional MR IID for GitLab API

        Returns:
            GitLab API response for the created comment

        Raises:
            CommentPublisherError: If publishing fails
        """
        try:
            # Format summary with proper structure
            formatted_summary = self._format_summary_comment(summary, mr_details)

            # Apply rate limiting
            self._apply_rate_limit()

            # Publish the summary
            response = self.gitlab_client.post_comment(
                formatted_summary,
                project_id=project_id,
                mr_iid=mr_iid
            )

            self.logger.info(
                "Published review summary",
                extra={
                    "comment_id": response.get("id"),
                    "summary_length": len(formatted_summary)
                }
            )

            return response

        except Exception as e:
            self.logger.error(f"Failed to publish review summary: {e}")
            raise CommentPublishError(f"Summary publishing failed: {e}")
    
    def publish_file_comments(
        self,
        comments: List[FormattedComment],
        mr_details: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Publish file-specific comments.

        Args:
            comments: List of formatted comments to publish
            mr_details: Optional MR details for inline comments
            project_id: Optional project ID for GitLab API
            mr_iid: Optional MR IID for GitLab API

        Returns:
            List of GitLab API responses for published comments

        Raises:
            CommentPublisherError: If publishing fails
        """
        if not comments:
            return []

        try:
            responses = []

            # Group comments by file for batching
            file_groups = self._group_comments_by_file(comments)

            for file_path, file_comments in file_groups.items():
                # Publish each comment with rate limiting
                for comment in file_comments:
                    formatted_comment = self._format_file_comment(comment)

                    # Apply rate limiting
                    self._apply_rate_limit()

                    # Publish the comment
                    if comment.line_number and mr_details:
                        # Inline comment - try with fallback
                        try:
                            response = self._publish_inline_comment(
                                comment, mr_details, formatted_comment,
                                project_id=project_id, mr_iid=mr_iid
                            )
                        except Exception as e:
                            # Check if this is a line_code/position error from GitLab
                            error_msg = str(e).lower()

                            # Check the exception and its cause chain for line_code errors
                            is_line_code_error = False
                            current_exception = e
                            while current_exception:
                                current_msg = str(current_exception).lower()
                                if ("line_code" in current_msg or "can't be blank" in current_msg or
                                    "must be a valid line code" in current_msg or
                                    ("bad request" in current_msg and "note" in current_msg)):
                                    is_line_code_error = True
                                    break
                                # Check __cause__ and __context__ for chained exceptions
                                current_exception = getattr(current_exception, '__cause__', None) or getattr(current_exception, '__context__', None)

                            if is_line_code_error:
                                self.logger.warning(
                                    f"GitLab rejected inline comment for {comment.file_path}:{comment.line_number}, "
                                    f"posting as general comment instead",
                                    extra={
                                        "file_path": comment.file_path,
                                        "line_number": comment.line_number,
                                        "error": str(e)
                                    }
                                )
                                # Post as general comment instead
                                fallback_comment = f"{formatted_comment}\n\n---\n*Note: This comment was intended for `{comment.file_path}:{comment.line_number}`, but GitLab rejected the inline position.*"
                                response = self.gitlab_client.post_comment(
                                    fallback_comment,
                                    project_id=project_id,
                                    mr_iid=mr_iid
                                )
                            else:
                                # Re-raise if it's a different error
                                raise
                    else:
                        # General file comment
                        response = self.gitlab_client.post_comment(
                            formatted_comment,
                            project_id=project_id,
                            mr_iid=mr_iid
                        )

                    responses.append(response)

            self.logger.info(
                "Published file comments",
                extra={
                    "total_comments": len(comments),
                    "files_affected": len(file_groups),
                    "published_count": len(responses)
                }
            )

            return responses

        except Exception as e:
            self.logger.error(f"Failed to publish file comments: {e}")
            raise CommentPublishError(f"File comment publishing failed: {e}")
    
    def _extract_comments_from_response(self, response_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract comment data from GLM response structure.
        
        Args:
            response_data: Parsed GLM response
            
        Returns:
            List of comment dictionaries
        """
        comments = []
        
        # Handle different response structures
        if "comments" in response_data:
            comments = response_data["comments"]
        elif "feedback" in response_data:
            comments = response_data["feedback"]
        elif "analysis" in response_data:
            comments = response_data["analysis"]
        else:
            # Assume the response itself contains comments
            comments = response_data if isinstance(response_data, list) else [response_data]
        
        return comments
    
    def _group_and_format_comments(self, comments: List[Dict[str, Any]]) -> CommentBatch:
        """
        Group comments by type and format them.
        
        Args:
            comments: List of raw comment dictionaries
            
        Returns:
            CommentBatch with formatted comments
        """
        batch = CommentBatch()
        
        for comment_data in comments:
            # Parse comment structure
            formatted_comment = self._parse_comment_data(comment_data)
            
            if formatted_comment.comment_type == CommentType.SUMMARY:
                batch.summary_comment = formatted_comment.body
            elif formatted_comment.line_number:
                batch.inline_comments.append(formatted_comment)
            else:
                batch.file_comments.append(formatted_comment)
        
        return batch
    
    def _parse_comment_data(self, comment_data: Dict[str, Any]) -> FormattedComment:
        """
        Parse individual comment data into FormattedComment.
        
        Args:
            comment_data: Raw comment dictionary
            
        Returns:
            FormattedComment instance
        """
        # Extract comment type
        comment_type_str = comment_data.get("type", comment_data.get("category", "suggestion")).lower()
        comment_type = CommentType(comment_type_str) if comment_type_str in CommentType._value2member_map_ else CommentType.SUGGESTION
        
        # Extract severity
        severity_str = comment_data.get("severity", comment_data.get("priority", "low")).lower()
        severity = SeverityLevel(severity_str) if severity_str in SeverityLevel._value2member_map_ else SeverityLevel.LOW
        
        # Extract file and line information
        file_path = comment_data.get("file", comment_data.get("path"))
        line_number = comment_data.get("line", comment_data.get("line_number"))

        # Parse line number (handle both single numbers and ranges like "37-49")
        if isinstance(line_number, str):
            try:
                # If it's a range (e.g., "37-49"), extract the first line number
                if '-' in line_number:
                    line_number = int(line_number.split('-')[0].strip())
                else:
                    line_number = int(line_number)
            except ValueError:
                line_number = None
        elif isinstance(line_number, (int, float)):
            line_number = int(line_number)
        
        return FormattedComment(
            comment_type=comment_type,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
            title=comment_data.get("title", comment_data.get("subject", "")),
            body=comment_data.get("message", comment_data.get("description", comment_data.get("comment", ""))),
            suggestion=comment_data.get("suggestion"),
            code_snippet=comment_data.get("code", comment_data.get("snippet")),
            metadata=comment_data.get("metadata", {})
        )
    
    def _format_summary_comment(
        self,
        summary: str,
        mr_details: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Format summary comment with proper structure.
        
        Args:
            summary: Raw summary text
            mr_details: Optional MR details
            
        Returns:
            Formatted markdown summary
        """
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        
        formatted = f"""# 🤖 Code Review Summary

{summary}

---

*Generated by GLM Code Review Bot at {timestamp}*"""
        
        return formatted
    
    def _format_file_comment(self, comment: FormattedComment) -> str:
        """
        Format individual file comment with markdown and emojis.
        
        Args:
            comment: FormattedComment to format
            
        Returns:
            Formatted markdown comment
        """
        severity_emoji = self.SEVERITY_EMOJIS.get(comment.severity, "")
        type_emoji = self.COMMENT_TYPE_EMOJIS.get(comment.comment_type, "")

        # Build comment header
        if comment.title:
            header = f"{severity_emoji} {type_emoji} **{comment.title}**"
        else:
            # If no title, use emojis only
            header = f"{severity_emoji} {type_emoji}"

        # Build comment body
        body_parts = [comment.body]
        
        if comment.code_snippet:
            body_parts.append("\n```")
            body_parts.append(comment.code_snippet)
            body_parts.append("```")
        
        if comment.suggestion:
            body_parts.append(f"\n**Suggestion:** {comment.suggestion}")
        
        # Add severity badge
        severity_badge = f"`{comment.severity.value.upper()}`"
        
        # Combine all parts
        formatted_parts = [header, severity_badge, "", *body_parts]
        
        # Add file context if available
        if comment.file_path:
            file_info = f"📁 `{comment.file_path}`"
            if comment.line_number:
                file_info += f":{comment.line_number}"
            formatted_parts.extend(["", file_info])
        
        return "\n".join(formatted_parts)
    
    def _group_comments_by_file(self, comments: List[FormattedComment]) -> Dict[str, List[FormattedComment]]:
        """
        Group comments by file path for efficient processing.
        
        Args:
            comments: List of formatted comments
            
        Returns:
            Dictionary mapping file paths to comment lists
        """
        file_groups = {}
        
        for comment in comments:
            file_path = comment.file_path or "general"
            if file_path not in file_groups:
                file_groups[file_path] = []
            file_groups[file_path].append(comment)
        
        return file_groups
    
    def _publish_inline_comment(
        self,
        comment: FormattedComment,
        mr_details: Dict[str, Any],
        formatted_comment: str,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish an inline comment to a specific line.

        Args:
            comment: Formatted comment data
            mr_details: MR details with SHA information
            formatted_comment: Formatted comment text
            project_id: Optional project ID for GitLab API
            mr_iid: Optional MR IID for GitLab API

        Returns:
            GitLab API response
        """
        self.logger.debug(
            f"Publishing inline comment for {comment.file_path}:{comment.line_number}, "
            f"validator={'present' if self.line_position_validator else 'MISSING'}"
        )

        # Initialize line position info
        line_info = None
        old_line = None
        line_code = None

        # Validate line position if validator is available
        if self.line_position_validator:
            self.logger.debug(
                f"Validating line position for {comment.file_path}:{comment.line_number}"
            )
            is_valid = self.line_position_validator.is_valid_position(
                comment.file_path,
                comment.line_number
            )

            if not is_valid:
                # Line is not in diff hunks, post as regular comment
                self.logger.warning(
                    f"Line {comment.line_number} is not in diff hunks for {comment.file_path}, "
                    f"posting as general comment instead",
                    extra={
                        "file_path": comment.file_path,
                        "line_number": comment.line_number
                    }
                )

                # Add file/line reference to comment
                fallback_comment = f"{formatted_comment}\n\n---\n*Note: This comment was intended for `{comment.file_path}:{comment.line_number}`, but that line is not part of the diff.*"
                return self.gitlab_client.post_comment(
                    fallback_comment,
                    project_id=project_id,
                    mr_iid=mr_iid
                )

            # Get detailed line info including old_line and line_code
            line_info = self.line_position_validator.get_line_info(
                comment.file_path,
                comment.line_number
            )

            if line_info:
                old_line = line_info.old_line
                line_code = line_info.line_code
                self.logger.debug(
                    f"Retrieved line info for {comment.file_path}:{comment.line_number}",
                    extra={
                        "old_line": old_line,
                        "line_code": line_code,
                        "line_type": line_info.line_type
                    }
                )

        # Extract SHA information from MR details
        base_sha = mr_details.get("diff_refs", {}).get("base_sha")
        start_sha = mr_details.get("diff_refs", {}).get("start_sha")
        head_sha = mr_details.get("diff_refs", {}).get("head_sha")

        if not all([base_sha, start_sha, head_sha]):
            # Fallback to regular comment if SHAs are not available
            self.logger.warning(
                "Missing SHA information, posting as general comment",
                extra={
                    "has_base_sha": base_sha is not None,
                    "has_start_sha": start_sha is not None,
                    "has_head_sha": head_sha is not None
                }
            )
            fallback_comment = f"{formatted_comment}\n\n---\n*Note: This comment was intended for `{comment.file_path}:{comment.line_number}`*"
            return self.gitlab_client.post_comment(
                fallback_comment,
                project_id=project_id,
                mr_iid=mr_iid
            )

        # Post inline comment
        return self.gitlab_client.post_inline_comment(
            body=formatted_comment,
            file_path=comment.file_path,
            line_number=comment.line_number,
            base_sha=base_sha,
            start_sha=start_sha,
            head_sha=head_sha,
            project_id=project_id,
            mr_iid=mr_iid
        )
    
    def _apply_rate_limit(self):
        """Apply rate limiting between API calls."""
        current_time = time.time()
        time_since_last_comment = current_time - self.last_comment_time
        
        if time_since_last_comment < self.comment_delay:
            sleep_time = self.comment_delay - time_since_last_comment
            self.logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f}s")
            time.sleep(sleep_time)
        
        self.last_comment_time = time.time()
    
    def publish_comment_batch(
        self,
        batch: CommentBatch,
        mr_details: Optional[Dict[str, Any]] = None,
        project_id: Optional[str] = None,
        mr_iid: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a complete batch of comments.

        Args:
            batch: CommentBatch to publish
            mr_details: Optional MR details for inline comments
            project_id: Optional project ID for GitLab API
            mr_iid: Optional MR IID for GitLab API

        Returns:
            Summary of published comments
        """
        results = {
            "summary_published": False,
            "file_comments_published": 0,
            "inline_comments_published": 0,
            "total_comments": 0,
            "errors": []
        }

        try:
            # Publish summary comment
            if batch.summary_comment:
                self.publish_review_summary(
                    batch.summary_comment,
                    mr_details,
                    project_id=project_id,
                    mr_iid=mr_iid
                )
                results["summary_published"] = True

            # Publish file comments
            all_file_comments = batch.file_comments + batch.inline_comments
            if all_file_comments:
                responses = self.publish_file_comments(
                    all_file_comments,
                    mr_details,
                    project_id=project_id,
                    mr_iid=mr_iid
                )
                results["file_comments_published"] = len(batch.file_comments)
                results["inline_comments_published"] = len(batch.inline_comments)
                results["total_comments"] = len(responses)

            self.logger.info(
                "Comment batch publication completed",
                extra=results
            )

        except Exception as e:
            error_msg = f"Failed to publish comment batch: {e}"
            self.logger.error(error_msg)
            results["errors"].append(error_msg)

        return results