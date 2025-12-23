"""
Line Position Validator for GitLab Inline Comments.

This module validates that line numbers are within the actual diff hunks
before attempting to post inline comments. GitLab only allows inline comments
on lines that are part of the diff (added, removed, or context lines).
"""

from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, field
import re
import hashlib

from src.utils.logger import get_logger


def calculate_line_code(file_path: str, old_line: Optional[int], new_line: Optional[int]) -> str:
    """
    Calculate GitLab line_code identifier.

    GitLab uses line_code format: {file_sha}_{old_line}_{new_line}
    where file_sha is SHA1 hash of the file path.

    Args:
        file_path: Path to the file
        old_line: Line number in old file (None for added lines)
        new_line: Line number in new file (None for removed lines)

    Returns:
        GitLab line_code string

    Raises:
        ValueError: If file_path is empty or if both old_line and new_line are None
    """
    # Validate inputs
    if not file_path or not file_path.strip():
        raise ValueError("file_path cannot be empty")

    if old_line is not None and old_line < 0:
        raise ValueError(f"old_line must be non-negative, got {old_line}")

    if new_line is not None and new_line < 0:
        raise ValueError(f"new_line must be non-negative, got {new_line}")

    if old_line is None and new_line is None:
        raise ValueError("At least one of old_line or new_line must be provided")

    file_sha = hashlib.sha1(file_path.encode('utf-8')).hexdigest()
    old = old_line if old_line is not None else ""
    new = new_line if new_line is not None else ""
    return f"{file_sha}_{old}_{new}"


@dataclass
class LinePositionInfo:
    """Information about a line position in a diff."""
    file_path: str
    line_number: int
    old_line: Optional[int]  # Line number in old file (None for new lines)
    line_type: str  # 'added', 'removed', 'context'
    in_diff_hunk: bool  # Whether this line is in a diff hunk
    line_code: str  # GitLab line_code identifier


@dataclass
class FileLineMapping:
    """Stores valid line positions for a file."""
    file_path: str
    valid_new_lines: Set[int] = field(default_factory=set)  # Line numbers that can receive comments
    line_info: Dict[int, LinePositionInfo] = field(default_factory=dict)  # Detailed line info
    _file_sha: Optional[str] = field(default=None, init=False, repr=False)  # Cached file SHA

    @property
    def file_sha(self) -> str:
        """Get cached file SHA1 hash."""
        if self._file_sha is None:
            self._file_sha = hashlib.sha1(self.file_path.encode('utf-8')).hexdigest()
        return self._file_sha

    def is_valid_line(self, line_number: int) -> bool:
        """Check if a line number is valid for inline comments."""
        return line_number in self.valid_new_lines

    def add_valid_line(self, line_number: int, old_line: Optional[int], line_type: str) -> None:
        """Add a valid line position."""
        self.valid_new_lines.add(line_number)

        # Calculate line_code for GitLab
        line_code = calculate_line_code(self.file_path, old_line, line_number)

        self.line_info[line_number] = LinePositionInfo(
            file_path=self.file_path,
            line_number=line_number,
            old_line=old_line,
            line_type=line_type,
            in_diff_hunk=True,
            line_code=line_code
        )

    def get_line_info(self, line_number: int) -> Optional[LinePositionInfo]:
        """Get detailed information about a line."""
        return self.line_info.get(line_number)


class LinePositionValidator:
    """
    Validates line positions from GitLab diff data.

    GitLab only allows inline comments on lines that are part of the diff hunks
    (added, removed, or context lines). This class tracks which line numbers
    are valid for inline commenting.
    """

    def __init__(self) -> None:
        """Initialize the line position validator."""
        self.logger = get_logger("line_position_validator")
        self.file_mappings: Dict[str, FileLineMapping] = {}

    def build_mappings_from_diff_data(self, diff_data: List[Dict[str, Any]]) -> None:
        """
        Build line position mappings from GitLab diff data.

        Args:
            diff_data: Raw diff data from GitLab API
        """
        self.file_mappings.clear()

        for file_diff in diff_data:
            file_path = file_diff.get("new_path") or file_diff.get("old_path")
            if not file_path:
                continue

            mapping = FileLineMapping(file_path=file_path)

            # Extract valid line positions from diff content
            diff_content = file_diff.get("diff", "")
            if diff_content:
                self._extract_valid_lines_from_diff(mapping, diff_content)

            # Store mapping
            self.file_mappings[file_path] = mapping

            self.logger.debug(
                f"Built line position mapping for {file_path}",
                extra={
                    "file_path": file_path,
                    "valid_lines_count": len(mapping.valid_new_lines)
                }
            )

        self.logger.info(
            f"Built line position mappings for {len(self.file_mappings)} files",
            extra={"total_files": len(self.file_mappings)}
        )

    def _extract_valid_lines_from_diff(
        self,
        mapping: FileLineMapping,
        diff_content: str
    ) -> None:
        """
        Extract valid line positions from diff content.

        This method parses the diff to find all lines that are part of the diff hunks,
        which are the only lines that can receive inline comments in GitLab.

        Args:
            mapping: FileLineMapping to populate
            diff_content: Raw diff content string
        """
        lines = diff_content.split('\n')
        current_new_line = 0
        current_old_line = 0
        in_hunk = False

        # Pattern for hunk header: @@ -old_line,old_count +new_line,new_count @@
        hunk_pattern = re.compile(r'@@ -(\d+)(?:,\d+)? \+(\d+)(?:,\d+)? @@')

        for line in lines:
            # Check for hunk header
            hunk_match = hunk_pattern.match(line)
            if hunk_match:
                # Start of a new hunk
                in_hunk = True
                current_old_line = int(hunk_match.group(1))
                current_new_line = int(hunk_match.group(2))
                continue

            if not in_hunk:
                continue

            # Process lines within hunks
            if line.startswith('+') and not line.startswith('+++'):
                # Added line - valid for inline comments
                if current_new_line > 0:
                    mapping.add_valid_line(current_new_line, None, 'added')
                current_new_line += 1
            elif line.startswith('-') and not line.startswith('---'):
                # Removed line - can't comment on removed lines in new version
                current_old_line += 1
            elif line.startswith(' '):
                # Context line - valid for inline comments
                if current_new_line > 0:
                    mapping.add_valid_line(current_new_line, current_old_line, 'context')
                current_old_line += 1
                current_new_line += 1
            elif line and not line.startswith('\\'):
                # Unknown line type, might be end of hunk
                in_hunk = False

    def is_valid_position(self, file_path: str, line_number: int) -> bool:
        """
        Check if a file and line number is valid for inline commenting.

        Args:
            file_path: Path to the file
            line_number: Line number in the file

        Returns:
            True if the position is valid for inline comments, False otherwise
        """
        self.logger.debug(
            f"Checking position validity: {file_path}:{line_number}, "
            f"total_mappings={len(self.file_mappings)}"
        )

        mapping = self.file_mappings.get(file_path)
        if not mapping:
            self.logger.warning(
                f"No mapping found for file {file_path}:{line_number}",
                extra={
                    "file_path": file_path,
                    "line_number": line_number,
                    "available_files": list(self.file_mappings.keys())[:5]  # First 5
                }
            )
            return False

        is_valid = mapping.is_valid_line(line_number)
        if not is_valid:
            self.logger.warning(
                f"Line {line_number} is NOT in diff hunks for {file_path}",
                extra={
                    "file_path": file_path,
                    "line_number": line_number,
                    "valid_lines": sorted(list(mapping.valid_new_lines))[:10]  # First 10 for logging
                }
            )
        else:
            self.logger.debug(
                f"Line {line_number} is VALID for {file_path}"
            )
        return is_valid

    def get_line_info(self, file_path: str, line_number: int) -> Optional[LinePositionInfo]:
        """
        Get detailed information about a line position.

        Args:
            file_path: Path to the file
            line_number: Line number in the file

        Returns:
            LinePositionInfo if found, None otherwise
        """
        mapping = self.file_mappings.get(file_path)
        if mapping:
            return mapping.get_line_info(line_number)
        return None

    def has_mapping(self, file_path: str) -> bool:
        """Check if a file has line position mappings."""
        return file_path in self.file_mappings

    def get_valid_line_numbers(self, file_path: str) -> List[int]:
        """Get all valid line numbers for inline comments in a file."""
        mapping = self.file_mappings.get(file_path)
        if mapping:
            return sorted(list(mapping.valid_new_lines))
        return []

    def find_nearest_valid_line(self, file_path: str, line_number: int) -> Optional[int]:
        """
        Find the nearest valid line number to the requested line.

        This is useful when a comment is requested for a line that's not in the diff,
        we can suggest posting it on a nearby valid line instead.

        Args:
            file_path: Path to the file
            line_number: Requested line number

        Returns:
            Nearest valid line number, or None if no valid lines exist
        """
        valid_lines = self.get_valid_line_numbers(file_path)
        if not valid_lines:
            return None

        # Find the closest line
        closest_line = min(valid_lines, key=lambda x: abs(x - line_number))
        return closest_line
