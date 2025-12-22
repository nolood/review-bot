"""
Diff parser for the GLM Code Review Bot.

This module handles parsing and processing GitLab diff format,
chunking large files, and filtering relevant files.

The module provides:
- FileDiff class for representing individual file diffs
- DiffChunk class for grouping files within token limits
- DiffParser class for parsing and processing GitLab diffs
- Utility functions for token estimation and line number parsing

Example:
    parser = DiffParser()
    file_diffs = parser.parse_gitlab_diff(diff_data)
    chunks = parser.chunk_large_diff(file_diffs)
    summary = parser.get_diff_summary(file_diffs)
"""

import re
import os
import fnmatch
from typing import List, Dict, Any, Optional, Tuple, Iterator, Literal, Union
from dataclasses import dataclass, field
from pathlib import Path
import logging

# Constants
DEFAULT_MAX_CHUNK_TOKENS = 50000
DEFAULT_CONTEXT_LINES = 3
TOP_LARGEST_FILES_COUNT = 5
TOKEN_ESTIMATION_RATIOS = {
    'code': 0.25,      # 1 token ≈ 4 characters of code
    'text': 0.75,      # 1 token ≈ 1.33 characters of English text
    'diff': 0.3        # Account for diff markers
}
PRIORITY_VALUES = {
    "HIGH": 0,
    "NORMAL": 1,
    "LOW": 3
}
CHANGE_TYPE_PRIORITY = {
    "modified": 0,
    "added": 1,
    "renamed": 2,
    "deleted": 3
}

# Language mapping for file extensions
LANGUAGE_MAPPING: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".rst": "rst",
    ".dockerfile": "dockerfile",
}

# Regular expression patterns
HUNK_HEADER_PATTERN = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
PLUS_LINE_PATTERN = re.compile(r'^\+')
MINUS_LINE_PATTERN = re.compile(r'^-')
CONTEXT_LINE_PATTERN = re.compile(r'^ ')

# Type aliases
ChangeType = Literal["added", "modified", "deleted", "renamed"]
ContentType = Literal["code", "text", "diff"]

# Import from actual modules with fallback for direct execution
try:
    from config.settings import settings
    from utils.exceptions import DiffParsingError, TokenLimitError
    from utils.logger import get_logger
except ImportError:
    # Fallback for direct execution during development
    class MockSettings:
        def __init__(self):
            self.max_diff_size = DEFAULT_MAX_CHUNK_TOKENS
            self.ignore_file_patterns = [
                "*.min.js", "*.min.css", "*.css.map", "*.js.map",
                "package-lock.json", "yarn.lock", "*.png", "*.jpg",
                "*.jpeg", "*.gif", "*.pdf", "*.zip"
            ]
            self.prioritize_file_patterns = [
                "*.py", "*.js", "*.ts", "*.jsx", "*.tsx", "*.java",
                "*.go", "*.rs", "*.cpp", "*.c", "*.h"
            ]
        
        def is_file_ignored(self, file_path: str) -> bool:
            """Check if a file should be ignored based on patterns."""
            return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_file_patterns)
        
        def is_file_prioritized(self, file_path: str) -> bool:
            """Check if a file should be prioritized based on patterns."""
            return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.prioritize_file_patterns)
    
    settings = MockSettings()
    
    class DiffParsingError(Exception):
        """Exception raised for errors in parsing diff content."""
        def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
            super().__init__(message)
            self.details = details or {}
    
    class TokenLimitError(Exception):
        """Exception raised when token limits are exceeded."""
        pass
    
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)

# Import tiktoken for token estimation
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False

# Initialize logger
logger = get_logger(__name__)

# Import tiktoken for token estimation
try:
    import tiktoken
    TIKTOKEN_AVAILABLE = True
except ImportError:
    tiktoken = None
    TIKTOKEN_AVAILABLE = False

# Constants
DEFAULT_MAX_CHUNK_TOKENS = 50000
DEFAULT_CONTEXT_LINES = 3
TOP_LARGEST_FILES_COUNT = 5
TOKEN_ESTIMATION_RATIOS = {
    'code': 0.25,      # 1 token ≈ 4 characters of code
    'text': 0.75,      # 1 token ≈ 1.33 characters of English text
    'diff': 0.3        # Account for diff markers
}
PRIORITY_VALUES = {
    "HIGH": 0,
    "NORMAL": 1,
    "LOW": 3
}
CHANGE_TYPE_PRIORITY = {
    "modified": 0,
    "added": 1,
    "renamed": 2,
    "deleted": 3
}

# Language mapping for file extensions
LANGUAGE_MAPPING: Dict[str, str] = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".cs": "csharp",
    ".php": "php",
    ".rb": "ruby",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".sh": "shell",
    ".sql": "sql",
    ".html": "html",
    ".css": "css",
    ".scss": "scss",
    ".sass": "sass",
    ".less": "less",
    ".xml": "xml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".json": "json",
    ".md": "markdown",
    ".rst": "rst",
    ".dockerfile": "dockerfile",
}

# Regular expression patterns
HUNK_HEADER_PATTERN = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
PLUS_LINE_PATTERN = re.compile(r'^\+')
MINUS_LINE_PATTERN = re.compile(r'^-')
CONTEXT_LINE_PATTERN = re.compile(r'^ ')

# Initialize logger
logger = get_logger(__name__)

# Type aliases
ChangeType = Literal["added", "modified", "deleted", "renamed"]
ContentType = Literal["code", "text", "diff"]


# ==============================
# Data Classes
# ==============================

@dataclass
class FileDiff:
    """
    Represents a single file's diff information.
    
    Attributes:
        old_path: Original file path
        new_path: New file path (for renames)
        file_mode: File mode change (e.g., "100644")
        change_type: Type of change (added, modified, deleted, renamed)
        hunks: List of hunk blocks in this file
        added_lines: Number of lines added
        removed_lines: Number of lines removed
        is_binary: Whether the file is binary
        file_extension: File extension for language detection
    """
    old_path: str
    new_path: str
    file_mode: str
    change_type: str
    hunks: List[str] = field(default_factory=list)
    added_lines: int = 0
    removed_lines: int = 0
    is_binary: bool = False
    file_extension: str = ""
    
    def __post_init__(self):
        """Post-initialization processing."""
        # Validate inputs
        if not self.old_path and not self.new_path:
            raise ValueError("At least one of old_path or new_path must be provided")
        
        # Extract file extension
        self._extract_file_extension()
    
    def _extract_file_extension(self) -> None:
        """Extract file extension from file path."""
        if self.new_path:
            self.file_extension = Path(self.new_path).suffix.lower()
        elif self.old_path:
            self.file_extension = Path(self.old_path).suffix.lower()
    
    @property
    def file_path(self) -> str:
        """Get the primary file path for this diff."""
        return self.new_path or self.old_path
    
    def get_content(self) -> str:
        """
        Get the full diff content for this file.
        
        Returns:
            Formatted diff content as string
        """
        content_parts = []
        
        # Add diff header
        if self.old_path != self.new_path:
            # File rename
            content_parts.append(f"diff --git a/{self.old_path} b/{self.new_path}")
        else:
            # Regular change
            content_parts.append(f"diff --git a/{self.file_path} b/{self.file_path}")
        
        if self.is_binary:
            content_parts.append("Binary files differ")
            return "\n".join(content_parts)
        
        # Add file mode line
        if self.change_type == "added":
            content_parts.append(f"new file mode {self.file_mode}")
        elif self.change_type == "deleted":
            content_parts.append(f"deleted file mode {self.file_mode}")
        
        # Add all hunks
        content_parts.extend(self.hunks)
        
        return "\n".join(content_parts)
    
    def estimate_tokens(self) -> int:
        """
        Estimate token count for this file diff.
        
        Returns:
            Estimated token count
        """
        if self.is_binary:
            return 0
        
        content = self.get_content()
        return estimate_tokens(content, "diff")


@dataclass
class DiffChunk:
    """
    Represents a chunk of diff data for processing.
    
    Chunks are used to split large diffs into manageable pieces
    that fit within token limits while preserving file boundaries.
    """
    files: List[FileDiff] = field(default_factory=list)
    estimated_tokens: int = 0
    
    def add_file(self, file_diff: FileDiff) -> None:
        """
        Add a file to this chunk.
        
        Args:
            file_diff: FileDiff object to add
        """
        if not isinstance(file_diff, FileDiff):
            raise TypeError("file_diff must be a FileDiff instance")
        
        self.files.append(file_diff)
        self.estimated_tokens += file_diff.estimate_tokens()
    
    def get_content(self) -> str:
        """
        Get the full content of this chunk.
        
        Returns:
            Concatenated diff content of all files in this chunk
        """
        return "\n".join(file_diff.get_content() for file_diff in self.files)
    
    def is_empty(self) -> bool:
        """
        Check if this chunk is empty.
        
        Returns:
            True if no files in this chunk
        """
        return len(self.files) == 0
    
    def exceeds_token_limit(self, max_tokens: int) -> bool:
        """
        Check if this chunk exceeds the token limit.
        
        Args:
            max_tokens: Maximum allowed tokens
            
        Returns:
            True if chunk exceeds limit
        """
        return self.estimated_tokens > max_tokens


# ==============================
# Main Parser Class
# ==============================

class DiffParser:
    """
    Parser for GitLab diff format with chunking and filtering capabilities.
    
    Handles parsing of diff strings from GitLab API responses,
    filtering irrelevant files, and chunking large diffs for
    processing within token limits.
    
    Example:
        parser = DiffParser()
        file_diffs = parser.parse_gitlab_diff(diff_data)
        chunks = parser.chunk_large_diff(file_diffs)
    """
    
    def __init__(self, max_chunk_tokens: Optional[int] = None):
        """
        Initialize the diff parser.
        
        Args:
            max_chunk_tokens: Maximum tokens per chunk (defaults to settings.max_diff_size)
            
        Raises:
            ValueError: If max_chunk_tokens is not a positive integer
        """
        # Validate input
        if max_chunk_tokens is not None and (not isinstance(max_chunk_tokens, int) or max_chunk_tokens <= 0):
            raise ValueError("max_chunk_tokens must be a positive integer")
        
        self.max_chunk_tokens = max_chunk_tokens or settings.max_diff_size
        self.logger = get_logger(f"{__name__}.{self.__class__.__name__}")
        
        # Initialize tokenizer if available
        self._initialize_tokenizer()
    
    def _initialize_tokenizer(self) -> None:
        """Initialize the tokenizer if tiktoken is available."""
        if TIKTOKEN_AVAILABLE and tiktoken is not None:
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
                self.logger.debug("Using tiktoken for token estimation")
            except Exception as e:
                self.logger.warning(f"Failed to initialize tiktoken: {e}")
                self.tokenizer = None
        else:
            self.tokenizer = None
            self.logger.debug("tiktoken not available, using character-based token estimation")
    
    def parse_gitlab_diff(self, diff_data: List[Dict[str, Any]]) -> List[FileDiff]:
        """
        Parse GitLab diff format into FileDiff objects.
        
        Args:
            diff_data: Raw diff data from GitLab API
            
        Returns:
            List of FileDiff objects
            
        Raises:
            DiffParsingError: If diff format is invalid
            TypeError: If diff_data is not a list of dictionaries
        """
        # Validate input
        if not isinstance(diff_data, list):
            raise TypeError("diff_data must be a list")
        
        try:
            file_diffs = []
            
            for i, diff_entry in enumerate(diff_data):
                if not isinstance(diff_entry, dict):
                    self.logger.warning(f"Skipping invalid diff entry at index {i}: not a dictionary")
                    continue
                
                try:
                    file_diff = self._parse_file_entry(diff_entry)
                    if file_diff:
                        file_diffs.append(file_diff)
                except Exception as e:
                    self.logger.error(f"Failed to parse diff entry at index {i}: {e}")
                    # Continue processing other entries
                    continue
            
            self.logger.info(
                f"Parsed {len(file_diffs)} file diffs from {len(diff_data)} entries",
                extra={
                    "parsed_files": len(file_diffs),
                    "total_entries": len(diff_data)
                }
            )
            return file_diffs
            
        except Exception as e:
            error = DiffParsingError(f"Failed to parse GitLab diff: {str(e)}")
            error.details["diff_content"] = str(diff_data)[:500]
            raise error from e
    
    def _parse_file_entry(self, diff_entry: Dict[str, Any]) -> Optional[FileDiff]:
        """
        Parse a single file diff entry.
        
        Args:
            diff_entry: Single file diff from GitLab API
            
        Returns:
            FileDiff object or None if file should be ignored
            
        Raises:
            TypeError: If diff_entry is not a dictionary
        """
        # Validate input
        if not isinstance(diff_entry, dict):
            raise TypeError("diff_entry must be a dictionary")
        
        # Extract file information
        old_path = diff_entry.get("old_path", "")
        new_path = diff_entry.get("new_path", "")
        
        # Validate file paths
        if not old_path and not new_path:
            self.logger.warning("Skipping diff entry: no file paths provided")
            return None
        
        # Determine change type
        change_type = self._determine_change_type(diff_entry, old_path, new_path)
        
        # Check if file should be ignored
        file_path = new_path or old_path
        if self._should_ignore_file(file_path):
            self.logger.debug(f"Ignoring file: {file_path}")
            return None
        
        # Get file mode
        file_mode = self._extract_file_mode(diff_entry, change_type)
        
        # Create FileDiff object
        file_diff = FileDiff(
            old_path=old_path,
            new_path=new_path,
            file_mode=file_mode,
            change_type=change_type,
            is_binary=diff_entry.get("binary_file", False)
        )
        
        # Parse diff content if available
        if "diff" in diff_entry:
            diff_content = diff_entry["diff"]
            if isinstance(diff_content, str):
                self._parse_diff_content(file_diff, diff_content)
            else:
                self.logger.warning(f"Invalid diff content type for file {file_path}: expected string")
        
        return file_diff
    
    def _determine_change_type(self, diff_entry: Dict[str, Any], old_path: str, new_path: str) -> str:
        """
        Determine the type of change from diff entry.
        
        Args:
            diff_entry: Diff entry dictionary
            old_path: Old file path
            new_path: New file path
            
        Returns:
            String indicating change type (added, modified, deleted, renamed)
        """
        if diff_entry.get("new_file"):
            return "added"
        elif diff_entry.get("deleted_file"):
            return "deleted"
        elif old_path != new_path:
            return "renamed"
        else:
            return "modified"
    
    def _extract_file_mode(self, diff_entry: Dict[str, Any], change_type: str) -> str:
        """
        Extract file mode from diff entry.
        
        Args:
            diff_entry: Diff entry dictionary
            change_type: Type of change
            
        Returns:
            File mode as string
        """
        # Try to get explicit file mode
        if "new_file" in diff_entry and diff_entry["new_file"]:
            file_mode = diff_entry.get("b_mode", "100644")
        elif "deleted_file" in diff_entry and diff_entry["deleted_file"]:
            file_mode = diff_entry.get("a_mode", "100644")
        else:
            file_mode = diff_entry.get("b_mode", "100644")
        
        # Default to 100644 if no mode found
        return file_mode if file_mode else "100644"
    
    def _parse_diff_content(self, file_diff: FileDiff, diff_content: str) -> None:
        """
        Parse the actual diff content for a file.
        
        Args:
            file_diff: FileDiff object to update
            diff_content: Raw diff content string
            
        Raises:
            TypeError: If diff_content is not a string
        """
        # Validate input
        if not isinstance(diff_content, str):
            raise TypeError("diff_content must be a string")
        
        if file_diff.is_binary or not diff_content:
            return
        
        lines = diff_content.split('\n')
        current_hunk = []
        added_lines = 0
        removed_lines = 0
        
        for line in lines:
            current_hunk.append(line)
            
            # Count line additions and removals using pre-compiled patterns
            if PLUS_LINE_PATTERN.match(line) and not line.startswith('+++'):
                added_lines += 1
            elif MINUS_LINE_PATTERN.match(line) and not line.startswith('---'):
                removed_lines += 1
        
        file_diff.hunks = current_hunk
        file_diff.added_lines = added_lines
        file_diff.removed_lines = removed_lines
    
    def chunk_large_diff(
        self, 
        file_diffs: List[FileDiff], 
        max_tokens: Optional[int] = None
    ) -> List[DiffChunk]:
        """
        Split file diffs into chunks within token limits.
        
        Args:
            file_diffs: List of FileDiff objects to chunk
            max_tokens: Maximum tokens per chunk
            
        Returns:
            List of DiffChunk objects
            
        Raises:
            TokenLimitError: If a single file exceeds token limits
            TypeError: If file_diffs is not a list
        """
        # Validate inputs
        if not isinstance(file_diffs, list):
            raise TypeError("file_diffs must be a list")
        
        if max_tokens is not None and (not isinstance(max_tokens, int) or max_tokens <= 0):
            raise ValueError("max_tokens must be a positive integer")
        
        max_tokens = max_tokens or self.max_chunk_tokens
        chunks = []
        current_chunk = DiffChunk()
        
        # Sort files by priority
        sorted_files = self._sort_files_by_priority(file_diffs)
        
        for file_diff in sorted_files:
            file_tokens = file_diff.estimate_tokens()
            
            # Check if single file exceeds limit
            if file_tokens > max_tokens:
                self.logger.warning(
                    f"File {file_diff.file_path} exceeds token limit: {file_tokens} > {max_tokens}",
                    extra={
                        "file_path": file_diff.file_path,
                        "file_tokens": file_tokens,
                        "max_tokens": max_tokens
                    }
                )
                # Create a chunk for this file anyway - GLM can handle larger inputs
                if current_chunk.files:
                    chunks.append(current_chunk)
                    current_chunk = DiffChunk()
                current_chunk.add_file(file_diff)
                chunks.append(current_chunk)
                current_chunk = DiffChunk()
                continue
            
            # Check if adding this file would exceed the chunk limit
            if current_chunk.estimated_tokens + file_tokens > max_tokens:
                # Save current chunk and start new one
                if not current_chunk.is_empty():
                    chunks.append(current_chunk)
                current_chunk = DiffChunk()
            
            # Add file to current chunk
            current_chunk.add_file(file_diff)
        
        # Add the last chunk if not empty
        if not current_chunk.is_empty():
            chunks.append(current_chunk)
        
        self.logger.info(
            f"Created {len(chunks)} chunks from {len(file_diffs)} files",
            extra={
                "total_chunks": len(chunks),
                "total_files": len(file_diffs),
                "max_tokens_per_chunk": max_tokens
            }
        )
        
        return chunks
    
    def _sort_files_by_priority(self, file_diffs: List[FileDiff]) -> List[FileDiff]:
        """
        Sort files by priority based on file patterns and change type.
        
        Args:
            file_diffs: List of FileDiff objects
            
        Returns:
            Sorted list of FileDiff objects
        """
        def get_priority(file_diff: FileDiff) -> Tuple[int, int, int]:
            # Primary priority: file pattern matching
            if settings.is_file_prioritized(file_diff.file_path):
                pattern_priority = PRIORITY_VALUES["HIGH"]
            elif settings.is_file_ignored(file_diff.file_path):
                pattern_priority = PRIORITY_VALUES["LOW"]
            else:
                pattern_priority = PRIORITY_VALUES["NORMAL"]
            
            # Secondary priority: change type
            change_priority = CHANGE_TYPE_PRIORITY.get(
                file_diff.change_type, 
                PRIORITY_VALUES["NORMAL"]
            )
            
            # Tertiary: file size (smaller files first)
            size_priority = file_diff.estimate_tokens()
            
            return (pattern_priority, change_priority, size_priority)
        
        return sorted(file_diffs, key=get_priority)
    
    def _should_ignore_file(self, file_path: str) -> bool:
        """
        Check if a file should be ignored based on patterns.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if file should be ignored
            
        Raises:
            TypeError: If file_path is not a string
        """
        if not isinstance(file_path, str):
            raise TypeError("file_path must be a string")
        
        return settings.is_file_ignored(file_path)
    
    def extract_file_context(
        self, 
        file_diff: FileDiff, 
        context_lines: int = DEFAULT_CONTEXT_LINES
    ) -> Dict[str, Any]:
        """
        Extract context information for a file diff.
        
        Args:
            file_diff: FileDiff object
            context_lines: Number of context lines to include
            
        Returns:
            Dictionary with file context information
            
        Raises:
            TypeError: If file_diff is not a FileDiff instance
            ValueError: If context_lines is not a positive integer
        """
        # Validate inputs
        if not isinstance(file_diff, FileDiff):
            raise TypeError("file_diff must be a FileDiff instance")
        
        if not isinstance(context_lines, int) or context_lines < 0:
            raise ValueError("context_lines must be a non-negative integer")
        
        context = {
            "file_path": file_diff.file_path,
            "file_extension": file_diff.file_extension,
            "change_type": file_diff.change_type,
            "added_lines": file_diff.added_lines,
            "removed_lines": file_diff.removed_lines,
            "is_binary": file_diff.is_binary,
            "estimated_tokens": file_diff.estimate_tokens()
        }
        
        # Add language-specific context
        if file_diff.file_extension:
            context["language"] = LANGUAGE_MAPPING.get(file_diff.file_extension, "unknown")
        
        return context
    
    def get_diff_summary(self, file_diffs: List[FileDiff]) -> Dict[str, Any]:
        """
        Generate a summary of the diff statistics.
        
        Args:
            file_diffs: List of FileDiff objects
            
        Returns:
            Dictionary with diff summary statistics
            
        Raises:
            TypeError: If file_diffs is not a list
        """
        # Validate input
        if not isinstance(file_diffs, list):
            raise TypeError("file_diffs must be a list")
        
        summary = {
            "total_files": len(file_diffs),
            "files_by_type": {},
            "total_added_lines": 0,
            "total_removed_lines": 0,
            "total_estimated_tokens": 0,
            "binary_files": 0,
            "largest_files": []
        }
        
        file_sizes = []
        
        for file_diff in file_diffs:
            # Validate file_diff
            if not isinstance(file_diff, FileDiff):
                self.logger.warning(f"Skipping invalid file_diff: {file_diff}")
                continue
            
            # Count by change type
            change_type = file_diff.change_type
            summary["files_by_type"][change_type] = summary["files_by_type"].get(change_type, 0) + 1
            
            # Count lines
            summary["total_added_lines"] += file_diff.added_lines
            summary["total_removed_lines"] += file_diff.removed_lines
            
            # Count tokens
            tokens = file_diff.estimate_tokens()
            summary["total_estimated_tokens"] += tokens
            
            # Count binary files
            if file_diff.is_binary:
                summary["binary_files"] += 1
            
            # Track largest files
            file_sizes.append((file_diff.file_path, tokens))
        
        # Sort and get top N largest files
        file_sizes.sort(key=lambda x: x[1], reverse=True)
        summary["largest_files"] = file_sizes[:TOP_LARGEST_FILES_COUNT]
        
        return summary


# ==============================
# Standalone Functions
# ==============================

def estimate_tokens(content: str, content_type: str = "code") -> int:
    """
    Estimate token count for content.
    
    Args:
        content: Text content to estimate tokens for
        content_type: Type of content (code, text, diff)
        
    Returns:
        Estimated token count
        
    Raises:
        TypeError: If content is not a string
        ValueError: If content_type is not valid
    """
    # Validate inputs
    if not isinstance(content, str):
        raise TypeError("content must be a string")
    
    if content_type not in ["code", "text", "diff"]:
        raise ValueError("content_type must be one of: code, text, diff")
    
    # Use tiktoken if available
    if TIKTOKEN_AVAILABLE and tiktoken is not None:
        try:
            tokenizer = tiktoken.get_encoding("cl100k_base")
            return len(tokenizer.encode(content))
        except Exception as e:
            logger.warning(f"Failed to use tiktoken for token estimation: {e}")
            # Continue with fallback
    
    # Fallback to character-based estimation
    ratio = TOKEN_ESTIMATION_RATIOS.get(content_type, TOKEN_ESTIMATION_RATIOS['code'])
    return int(len(content) * ratio)


def parse_diff_line_numbers(hunk_content: str) -> List[Tuple[Optional[int], Optional[int], str]]:
    """
    Parse line numbers from hunk content.
    
    Args:
        hunk_content: Hunk diff content
        
    Returns:
        List of tuples (old_line, new_line, content)
        
    Raises:
        TypeError: If hunk_content is not a string
    """
    # Validate input
    if not isinstance(hunk_content, str):
        raise TypeError("hunk_content must be a string")
    
    lines = []
    old_line = None
    new_line = None
    
    # Extract hunk header (e.g., "@@ -10,7 +10,7 @@")
    hunk_header_match = HUNK_HEADER_PATTERN.search(hunk_content)
    if hunk_header_match:
        old_line = int(hunk_header_match.group(1))
        new_line = int(hunk_header_match.group(3))
    
    if old_line is None or new_line is None:
        return lines
    
    # Parse each line in the hunk
    for line in hunk_content.split('\n'):
        if line.startswith('@@'):
            # New hunk header
            hunk_header_match = HUNK_HEADER_PATTERN.search(line)
            if hunk_header_match:
                old_line = int(hunk_header_match.group(1))
                new_line = int(hunk_header_match.group(3))
            continue
        elif line.startswith('-'):
            # Removed line
            lines.append((old_line, None, line[1:]))
            old_line += 1
        elif line.startswith('+'):
            # Added line
            lines.append((None, new_line, line[1:]))
            new_line += 1
        elif line.startswith(' '):
            # Context line
            lines.append((old_line, new_line, line[1:]))
            old_line += 1
            new_line += 1
        # Skip other lines (file headers, etc.)
    
    return lines