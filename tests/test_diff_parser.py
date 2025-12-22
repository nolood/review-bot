"""
Unit tests for diff parser
"""
import pytest
from src.diff_parser import DiffParser


class TestDiffParser:
    """Test cases for DiffParser class"""

    def test_parse_simple_diff(self):
        """Test parsing a simple diff with one file"""
        diff_lines = [
            "--- a/src/example.py",
            "+++ b/src/example.py",
            "@@ -10,7 +10,7 @@",
            " class Calculator:",
            "     def add(self, a, b):",
            '         """Add two numbers"""',
            "-        return a + b",
            "+        return float(a) + float(b)"
        ]
        diff_text = "\n".join(diff_lines)

        parser = DiffParser()
        result = parser.parse_diff(diff_text)

        assert len(result) == 1
        file_diff = result[0]
        assert file_diff.path == "src/example.py"
        assert len(file_diff.changes) == 2

        # Check deletion
        deletion = file_diff.changes[0]
        assert deletion.type == "deletion"
        assert deletion.content == "        return a + b"

        # Check addition
        addition = file_diff.changes[1]
        assert addition.type == "addition"
        assert addition.content == "        return float(a) + float(b)"

    def test_parse_empty_diff(self):
        """Test parsing an empty diff"""
        parser = DiffParser()
        result = parser.parse_diff("")
        assert result == []

    def test_chunk_diff_small(self):
        """Test chunking a small diff that doesn't need splitting"""
        diff_lines = [
            "--- a/src/example.py",
            "+++ b/src/example.py",
            "@@ -10,7 +10,7 @@",
            " class Calculator:",
            "     def add(self, a, b):",
            '         """Add two tokens"""',
            "-        return a + b",
            "+        return float(a) + float(b)"
        ]
        diff_text = "\n".join(diff_lines)

        parser = DiffParser()
        chunks = parser.chunk_diff(diff_text, max_tokens=1000)

        assert len(chunks) == 1
        assert chunks[0] == diff_text

    def test_estimate_tokens(self):
        """Test token estimation for different content types"""
        parser = DiffParser()
        code = "def hello_world():\n    return True"
        tokens = parser._estimate_tokens(code, "code")
        assert tokens > 0
        assert tokens < len(code)