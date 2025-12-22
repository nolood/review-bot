"""
GLM API client for code review analysis.

This module provides a client for interacting with the GLM API to analyze
code changes and generate structured feedback.
"""

import json
import os
import re
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import httpx

from src.config.prompts import get_system_prompt, ReviewType
from src.utils.logger import api_logger
from src.utils.exceptions import GLMAPIError, ReviewBotError
from src.utils.retry import retry_with_backoff, RetryConfig


class TokenUsage:
    """Token usage tracking for API calls."""
    
    def __init__(self, prompt_tokens: int = 0, completion_tokens: int = 0, total_tokens: int = 0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.total_tokens = total_tokens
        self.timestamp = datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "total_tokens": self.total_tokens,
            "timestamp": self.timestamp.isoformat()
        }


class GLMClient:
    """
    Client for interacting with GLM API for code review analysis.
    
    This client handles API communication, response parsing, and error handling
    for code review tasks using the GLM model.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: str = "glm-4",
        temperature: float = 0.3,
        max_tokens: int = 4000,
        timeout: int = 60
    ):
        """
        Initialize GLM API client.
        
        Args:
            api_key: GLM API key (defaults to GLM_API_KEY env var)
            api_url: GLM API URL (defaults to GLM_API_URL env var or standard URL)
            model: Model name to use (default: glm-4)
            temperature: Temperature for response generation (0.0-1.0)
            max_tokens: Maximum tokens in response
            timeout: Request timeout in seconds
        """
        self.api_key = api_key or os.getenv("GLM_API_KEY")
        if not self.api_key:
            raise ValueError("GLM API key is required. Set GLM_API_KEY environment variable.")
        
        self.api_url = api_url or os.getenv(
            "GLM_API_URL", 
            "https://api.z.ai/api/paas/v4/chat/completions"
        )
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        
        # Token usage tracking
        self.token_usage: List[TokenUsage] = []
        
        # Retry configuration
        self.retry_config = RetryConfig(
            max_retries=3,
            initial_delay=1.0,
            max_delay=30.0,
            backoff_factor=2.0
        )
        
        api_logger.logger.info(f"GLM client initialized with model: {model}")
    
    def analyze_code(
        self,
        diff_content: str,
        custom_prompt: Optional[str] = None,
        review_type: ReviewType = ReviewType.GENERAL,
        stream: bool = False
    ) -> Dict[str, Any]:
        """
        Analyze code changes using GLM API.
        
        Args:
            diff_content: Git diff content to analyze
            custom_prompt: Optional custom prompt instructions
            review_type: Type of review to perform
            stream: Whether to use streaming response
            
        Returns:
            Dictionary containing analysis results and comments
            
        Raises:
            GLMAPIError: If API call fails or response is invalid
        """
        if not diff_content.strip():
            raise ValueError("Diff content cannot be empty")
        
        # Check token limits
        estimated_tokens = self._estimate_tokens(diff_content, "diff")
        if estimated_tokens > self.max_tokens * 0.8:  # Leave room for response
            api_logger.logger.warning(
                f"Large diff detected: {estimated_tokens} tokens. "
                f"Consider splitting into smaller chunks."
            )
        
        # Prepare request
        system_prompt = custom_prompt or get_system_prompt(review_type)
        user_content = self._get_default_prompt() + f"\n\nDiff to analyze:\n{diff_content}"
        
        if custom_prompt:
            user_content = f"{custom_prompt}\n\n{user_content}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content}
        ]
        
        request_data = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "stream": stream
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        api_logger.logger.info(
            f"Analyzing code with {review_type.value} review type, "
            f"estimated tokens: {estimated_tokens}"
        )
        
        try:
            # Make API call with retry
            response = self._make_api_request(request_data, headers)
            
            # Parse and return results
            result = self._parse_response(response)
            
            # Track token usage
            if "usage" in response:
                usage = TokenUsage(
                    prompt_tokens=response["usage"].get("prompt_tokens", 0),
                    completion_tokens=response["usage"].get("completion_tokens", 0),
                    total_tokens=response["usage"].get("total_tokens", 0)
                )
                self.token_usage.append(usage)
                result["usage"] = usage.to_dict()
            
            api_logger.logger.info(
                f"Code analysis completed. Generated {len(result.get('comments', []))} comments"
            )
            
            return result
            
        except Exception as e:
            api_logger.logger.error(f"Code analysis failed: {str(e)}")
            raise GLMAPIError(f"Failed to analyze code: {str(e)}") from e
    
    def _make_api_request(self, request_data: Dict[str, Any], headers: Dict[str, str]) -> Dict[str, Any]:
        """Make API request with retry logic."""
        
        @retry_with_backoff(self.retry_config)
        def _request():
            try:
                with httpx.Client(timeout=self.timeout) as client:
                    response = client.post(
                        self.api_url,
                        json=request_data,
                        headers=headers
                    )
                    response.raise_for_status()
                    return response.json()
                
            except httpx.TimeoutException as e:
                raise GLMAPIError(f"Request timeout after {self.timeout}s") from e
            except httpx.ConnectError as e:
                raise GLMAPIError("Connection error to GLM API") from e
            except httpx.HTTPStatusError as e:
                error_msg = f"HTTP error: {e.response.status_code}"
                if e.response.text:
                    try:
                        error_detail = e.response.json()
                        error_msg += f" - {error_detail.get('error', {}).get('message', e.response.text)}"
                    except:
                        error_msg += f" - {e.response.text}"
                raise GLMAPIError(error_msg) from e
            except httpx.RequestError as e:
                raise GLMAPIError(f"Request failed: {str(e)}") from e
        
        return _request()
    
    def _get_default_prompt(self) -> str:
        """
        Get the default user prompt for code analysis.
        
        Returns:
            Default prompt string requesting JSON-formatted analysis
        """
        return """Analyze this code and provide structured feedback in JSON format:

{
  "comments": [
    {
      "file": "path/to/file.py",
      "line": 42,
      "comment": "Consider using list comprehension here",
      "type": "suggestion|issue|praise",
      "severity": "low|medium|high|critical"
    }
  ]
}

Focus on:
- Code quality and maintainability
- Potential bugs or issues
- Performance considerations
- Security best practices
- Code style and conventions

Provide specific, actionable feedback with line numbers when applicable."""
    
    def _parse_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse GLM API response and extract structured feedback.
        
        Args:
            response: Raw API response dictionary
            
        Returns:
            Parsed response with standardized format
            
        Raises:
            GLMAPIError: If response format is invalid
        """
        if not response.get("choices"):
            raise GLMAPIError("Invalid response format: missing choices")
        
        choice = response["choices"][0]
        message = choice.get("message", {})
        content = message.get("content", "")
        
        if not content:
            raise GLMAPIError("Invalid response format: missing content")
        
        # Try to parse as JSON first
        try:
            parsed_content = json.loads(content)
            if isinstance(parsed_content, dict) and "comments" in parsed_content:
                # Ensure all comments have required fields
                for comment in parsed_content["comments"]:
                    comment.setdefault("severity", "medium")
                    comment.setdefault("type", "suggestion")
                    comment.setdefault("file", "unknown")
                    comment.setdefault("line", None)
                return parsed_content
        except (json.JSONDecodeError, KeyError):
            # Fall back to text parsing
            pass
        
        # If JSON parsing fails, treat as text and create a single comment
        api_logger.logger.warning("Response was not valid JSON, treating as text")
        
        return {
            "comments": [
                {
                    "file": "unknown",
                    "line": None,
                    "comment": content.strip(),
                    "type": "suggestion",
                    "severity": "medium"
                }
            ]
        }
    
    def _estimate_tokens(self, content: str, content_type: str = "text") -> int:
        """
        Estimate token count for content before sending to API.
        
        Args:
            content: Content to estimate tokens for
            content_type: Type of content (text, code, diff)
            
        Returns:
            Estimated token count
        """
        if not content:
            return 0
        
        # Simple token estimation based on content type
        if content_type == "code":
            # Code typically has more tokens per character due to syntax
            return int(len(content) * 0.7)
        elif content_type == "diff":
            # Diffs have meta characters that increase token count
            return int(len(content) * 0.8)
        else:
            # General text: approximately 4 characters per token
            return int(len(content) * 0.25)
    
    def get_token_usage_stats(self) -> Dict[str, Any]:
        """
        Get token usage statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        if not self.token_usage:
            return {"total_requests": 0, "total_tokens": 0}
        
        total_requests = len(self.token_usage)
        total_tokens = sum(usage.total_tokens for usage in self.token_usage)
        avg_tokens = total_tokens / total_requests if total_requests > 0 else 0
        
        return {
            "total_requests": total_requests,
            "total_tokens": total_tokens,
            "average_tokens_per_request": avg_tokens,
            "prompt_tokens_total": sum(usage.prompt_tokens for usage in self.token_usage),
            "completion_tokens_total": sum(usage.completion_tokens for usage in self.token_usage)
        }
    
    def reset_token_usage(self) -> None:
        """Reset token usage tracking."""
        self.token_usage.clear()
        api_logger.logger.info("Token usage tracking reset")