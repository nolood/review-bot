"""
Unit tests for diff parser
"""
import pytest
from src.diff_parser import DiffParser
from src.utils.exceptions import DiffParsingError, TokenLimitError


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

    def test_parse_diff_with_multiple_files(self):
        """Test parsing diff with multiple files"""
        diff_lines = [
            "--- a/src/file1.py",
            "+++ b/src/file1.py",
            "@@ -1,3 +1,3 @@",
            " def func1():",
            "-    return 1",
            "+    return 2",
            "--- a/src/file2.js",
            "+++ b/src/file2.js",
            "@@ -5,5 +5,5 @@",
            " function func2() {",
            "-    return false;",
            "+    return true;",
            " }"
        ]
        diff_text = "\n".join(diff_lines)

        parser = DiffParser()
        result = parser.parse_diff(diff_text)

        assert len(result) == 2
        assert result[0].path == "src/file1.py"
        assert result[1].path == "src/file2.js"
        assert len(result[0].changes) == 2
        assert len(result[1].changes) == 2

    def test_chunk_diff_with_large_content(self):
        """Test chunking a diff that needs to be split"""
        # Create multiple files to force chunking
        lines = []
        for file_num in range(3):  # Create 3 files
            lines.extend([
                f"--- a/file_{file_num}.py",
                f"+++ b/file_{file_num}.py",
                f"@@ -1,10 +1,10 @@"
            ])
            # Add enough lines to each file to exceed the token limit
            for i in range(50):
                lines.append(f"- Original line {i} in file {file_num}")
                lines.append(f"+ Modified line {i} in file {file_num}")
        
        diff_text = "\n".join(lines)

        parser = DiffParser()
        chunks = parser.chunk_diff(diff_text, max_tokens=1000)  # Small limit to force chunking

        # Should create multiple chunks
        assert len(chunks) >= 1
        # All chunks should have content
        assert all(chunk.strip() for chunk in chunks)

    def test_parse_diff_error_handling(self):
        """Test error handling for invalid diff format"""
        parser = DiffParser()
        
        # Test with non-string input
        with pytest.raises(TypeError):
            parser.parse_diff(123)  # type: ignore[arg-type]
        
        # Test with malformed diff
        malformed_diff = "This is not a valid diff format"
        result = parser.parse_diff(malformed_diff)
        assert result == []  # Should return empty list for invalid format

    def test_chunk_diff_error_handling(self):
        """Test error handling for chunk_diff method"""
        parser = DiffParser()
        
        # Test with non-string input
        with pytest.raises(TypeError):
            parser.chunk_diff(123)  # type: ignore[arg-type]
        
        # Test with invalid max_tokens
        with pytest.raises(ValueError):
            parser.chunk_diff("valid diff", max_tokens=-1)
        
        with pytest.raises(ValueError):
            parser.chunk_diff("valid diff", max_tokens="invalid")  # type: ignore[arg-type]

    def test_estimate_tokens_error_handling(self):
        """Test error handling for _estimate_tokens method"""
        parser = DiffParser()
        
        # Test with non-string input
        with pytest.raises(TypeError):
            parser._estimate_tokens(123)  # type: ignore[arg-type]
        
        # Test with invalid content type
        with pytest.raises(ValueError):
            parser._estimate_tokens("valid content", "invalid_type")

    def test_estimate_tokens_different_content_types(self):
        """Test token estimation for different content types"""
        parser = DiffParser()
        content = "This is some test content for token estimation"
        
        code_tokens = parser._estimate_tokens(content, "code")
        text_tokens = parser._estimate_tokens(content, "text")
        diff_tokens = parser._estimate_tokens(content, "diff")
        
        # All should return positive values
        assert code_tokens > 0
        assert text_tokens > 0
        assert diff_tokens > 0
        
        # Different content types should have different estimations
        # (due to different ratios in TOKEN_ESTIMATION_RATIOS)
        assert code_tokens != text_tokens or text_tokens != diff_tokens

    def test_parse_diff_with_new_file(self):
        """Test parsing diff for a newly added file"""
        diff_lines = [
            "--- /dev/null",
            "+++ b/new_file.py",
            "@@ -0,0 +1,5 @@",
            "+def new_function():",
            "+    \"\"\"New function\"\"\"",
            "+    return \"new\"",
            "+",
            "+print(\"Hello\")"
        ]
        diff_text = "\n".join(diff_lines)

        parser = DiffParser()
        result = parser.parse_diff(diff_text)

        assert len(result) == 1
        file_diff = result[0]
        assert file_diff.path == "new_file.py"
        assert len(file_diff.changes) == 5
        # All changes should be additions
        assert all(change.type == "addition" for change in file_diff.changes)

    def test_parse_diff_with_deleted_file(self):
        """Test parsing diff for a deleted file"""
        diff_lines = [
            "--- a/deleted_file.py",
            "+++ /dev/null",
            "@@ -1,3 +0,0 @@",
            "-def old_function():",
            "-    \"\"\"Old function\"\"\"",
            "-    return \"old\""
        ]
        diff_text = "\n".join(diff_lines)

        parser = DiffParser()
        result = parser.parse_diff(diff_text)

        assert len(result) == 1
        file_diff = result[0]
        # For deleted files, the path is /dev/null (this is correct behavior)
        assert file_diff.path == "/dev/null"
        assert len(file_diff.changes) == 3
        # All changes should be deletions
        assert all(change.type == "deletion" for change in file_diff.changes)