#!/usr/bin/env python3
"""
Test script for the refactored DiffParser class.

This script verifies that the DiffParser works correctly by testing:
1. Import and initialization
2. Simple diff parsing
3. Chunking functionality
4. Error handling
"""

import sys
import os
from typing import List, Dict, Any

# Add src directory to Python path to allow direct imports
src_path = os.path.join(os.path.dirname(__file__), 'src')
sys.path.insert(0, src_path)

def test_import_and_initialization():
    """Test importing DiffParser and creating instances."""
    print("Testing import and initialization...")
    
    try:
        import diff_parser as diff_parser_module
        DiffParser = diff_parser_module.DiffParser
        print("✓ Successfully imported DiffParser")
    except ImportError as e:
        print(f"✗ Failed to import DiffParser: {e}")
        return False
    
    try:
        # Test default initialization
        parser = DiffParser()
        print("✓ Successfully created DiffParser with default settings")
        
        # Test initialization with custom token limit
        parser_custom = DiffParser(max_chunk_tokens=1000)
        print("✓ Successfully created DiffParser with custom token limit")
        
    except Exception as e:
        print(f"✗ Failed to initialize DiffParser: {e}")
        return False
    
    return True

def create_sample_diff_data() -> List[Dict[str, Any]]:
    """Create sample GitLab diff data for testing."""
    return [
        {
            "old_path": "src/main.py",
            "new_path": "src/main.py",
            "new_file": False,
            "deleted_file": False,
            "a_mode": "100644",
            "b_mode": "100644",
            "binary_file": False,
            "diff": """@@ -1,5 +1,7 @@
 def hello_world():
-    print("Hello, World!")
+    print("Hello, Enhanced World!")
+    # Added a comment
+    return True
 
 if __name__ == "__main__":
"""
        },
        {
            "old_path": "",
            "new_path": "src/utils.py",
            "new_file": True,
            "deleted_file": False,
            "b_mode": "100644",
            "binary_file": False,
            "diff": """@@ -0,0 +1,3 @@
+def utility_function():
+    return "utility"
+
"""
        },
        {
            "old_path": "old_file.txt",
            "new_path": "renamed_file.txt",
            "new_file": False,
            "deleted_file": False,
            "a_mode": "100644",
            "b_mode": "100644",
            "binary_file": False,
            "diff": """@@ -1,2 +1,2 @@
-Old content
+New content
 Renamed content
"""
        }
    ]

def test_simple_diff_parsing():
    """Test parsing a simple diff structure."""
    print("\nTesting simple diff parsing...")
    
    try:
        import diff_parser as diff_parser_module
        DiffParser = diff_parser_module.DiffParser
        FileDiff = diff_parser_module.FileDiff
        
        parser = DiffParser()
        diff_data = create_sample_diff_data()
        
        # Parse the diff
        file_diffs = parser.parse_gitlab_diff(diff_data)
        
        print(f"✓ Successfully parsed {len(file_diffs)} file diffs")
        
        # Verify file diffs
        assert len(file_diffs) == 3, f"Expected 3 file diffs, got {len(file_diffs)}"
        
        # Check first file (modified)
        main_py = file_diffs[0]
        assert main_py.file_path == "src/main.py", f"Expected src/main.py, got {main_py.file_path}"
        assert main_py.change_type == "modified", f"Expected modified, got {main_py.change_type}"
        # The parser correctly counts all lines starting with + (including the comment line)
        assert main_py.added_lines == 3, f"Expected 3 added lines, got {main_py.added_lines}"
        assert main_py.removed_lines == 1, f"Expected 1 removed line, got {main_py.removed_lines}"
        print("✓ Modified file parsed correctly")
        
        # Check second file (added)
        utils_py = file_diffs[1]
        assert utils_py.file_path == "src/utils.py", f"Expected src/utils.py, got {utils_py.file_path}"
        assert utils_py.change_type == "added", f"Expected added, got {utils_py.change_type}"
        assert utils_py.added_lines == 3, f"Expected 3 added lines, got {utils_py.added_lines}"
        assert utils_py.removed_lines == 0, f"Expected 0 removed lines, got {utils_py.removed_lines}"
        print("✓ Added file parsed correctly")
        
        # Check third file (renamed)
        renamed_txt = file_diffs[2]
        assert renamed_txt.file_path == "renamed_file.txt", f"Expected renamed_file.txt, got {renamed_txt.file_path}"
        assert renamed_txt.change_type == "renamed", f"Expected renamed, got {renamed_txt.change_type}"
        assert renamed_txt.old_path == "old_file.txt", f"Expected old_file.txt, got {renamed_txt.old_path}"
        print("✓ Renamed file parsed correctly")
        
        # Test FileDiff methods
        content = main_py.get_content()
        assert "def hello_world():" in content, "File content should contain function definition"
        assert "+    print(\"Hello, Enhanced World!\")" in content, "File content should contain added line"
        print("✓ FileDiff.get_content() works correctly")
        
        # Test token estimation
        tokens = main_py.estimate_tokens()
        assert tokens > 0, "Token estimation should return positive value"
        print(f"✓ Token estimation works: {tokens} tokens")
        
        return True
        
    except Exception as e:
        print(f"✗ Simple diff parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_chunking_functionality():
    """Test diff chunking functionality."""
    print("\nTesting chunking functionality...")
    
    try:
        import diff_parser as diff_parser_module
        DiffParser = diff_parser_module.DiffParser
        DiffChunk = diff_parser_module.DiffChunk
        
        parser = DiffParser(max_chunk_tokens=100)  # Small limit to force chunking
        diff_data = create_sample_diff_data()
        
        # Parse the diff
        file_diffs = parser.parse_gitlab_diff(diff_data)
        
        # Test chunking
        chunks = parser.chunk_large_diff(file_diffs)
        
        print(f"✓ Successfully created {len(chunks)} chunks")
        
        # Verify chunks
        assert len(chunks) >= 1, "Should have at least one chunk"
        
        # Check that all files are in chunks
        total_files_in_chunks = sum(len(chunk.files) for chunk in chunks)
        assert total_files_in_chunks == len(file_diffs), f"Expected {len(file_diffs)} files in chunks, got {total_files_in_chunks}"
        
        # Test chunk methods
        for i, chunk in enumerate(chunks):
            content = chunk.get_content()
            assert content, f"Chunk {i} should have content"
            assert not chunk.is_empty(), f"Chunk {i} should not be empty"
            print(f"✓ Chunk {i}: {len(chunk.files)} files, {chunk.estimated_tokens} tokens")
        
        # Test with larger token limit (should result in fewer chunks)
        parser_large = DiffParser(max_chunk_tokens=10000)
        chunks_large = parser_large.chunk_large_diff(file_diffs)
        assert len(chunks_large) <= len(chunks), "Larger token limit should result in fewer or equal chunks"
        print(f"✓ Larger token limit results in {len(chunks_large)} chunks")
        
        return True
        
    except Exception as e:
        print(f"✗ Chunking functionality failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """Test error handling for various edge cases."""
    print("\nTesting error handling...")
    
    try:
        import diff_parser as diff_parser_module
        DiffParser = diff_parser_module.DiffParser
        DiffParsingError = diff_parser_module.DiffParsingError
        TokenLimitError = diff_parser_module.TokenLimitError
        
        parser = DiffParser()
        
        # Test invalid input types
        try:
            parser.parse_gitlab_diff("not a list")
            print("✗ Should have raised TypeError for non-list input")
            return False
        except TypeError:
            print("✓ Correctly raised TypeError for non-list input")
        
        try:
            parser.parse_gitlab_diff([{"invalid": "entry"}])
            # This should work but log a warning
            print("✓ Handled invalid diff entry gracefully")
        except Exception as e:
            print(f"✗ Failed to handle invalid diff entry: {e}")
            return False
        
        # Test invalid initialization parameters
        try:
            DiffParser(max_chunk_tokens=-1)
            print("✗ Should have raised ValueError for negative token limit")
            return False
        except ValueError:
            print("✓ Correctly raised ValueError for negative token limit")
        
        try:
            DiffParser(max_chunk_tokens="not a number")
            print("✗ Should have raised ValueError for non-integer token limit")
            return False
        except ValueError:
            print("✓ Correctly raised ValueError for non-integer token limit")
        
        # Test FileDiff validation
        FileDiff = diff_parser_module.FileDiff
        try:
            FileDiff(old_path="", new_path="", file_mode="100644", change_type="added")
            print("✗ Should have raised ValueError for empty file paths")
            return False
        except ValueError:
            print("✓ Correctly raised ValueError for empty file paths")
        
        # Test DiffChunk validation
        DiffChunk = diff_parser_module.DiffChunk
        chunk = DiffChunk()
        try:
            chunk.add_file("not a FileDiff")
            print("✗ Should have raised TypeError for non-FileDiff input")
            return False
        except TypeError:
            print("✓ Correctly raised TypeError for non-FileDiff input")
        
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_additional_features():
    """Test additional features like summary and context extraction."""
    print("\nTesting additional features...")
    
    try:
        import diff_parser as diff_parser_module
        DiffParser = diff_parser_module.DiffParser
        
        parser = DiffParser()
        diff_data = create_sample_diff_data()
        file_diffs = parser.parse_gitlab_diff(diff_data)
        
        # Test diff summary
        summary = parser.get_diff_summary(file_diffs)
        
        expected_keys = [
            "total_files", "files_by_type", "total_added_lines", 
            "total_removed_lines", "total_estimated_tokens", 
            "binary_files", "largest_files"
        ]
        
        for key in expected_keys:
            assert key in summary, f"Summary should contain {key}"
        
        assert summary["total_files"] == 3, f"Expected 3 total files, got {summary['total_files']}"
        assert summary["files_by_type"]["modified"] == 1, "Should have 1 modified file"
        assert summary["files_by_type"]["added"] == 1, "Should have 1 added file"
        assert summary["files_by_type"]["renamed"] == 1, "Should have 1 renamed file"
        
        print(f"✓ Diff summary generated: {summary['total_files']} files, {summary['total_estimated_tokens']} tokens")
        
        # Test file context extraction
        context = parser.extract_file_context(file_diffs[0])
        
        expected_context_keys = [
            "file_path", "file_extension", "change_type", 
            "added_lines", "removed_lines", "is_binary", "estimated_tokens"
        ]
        
        for key in expected_context_keys:
            assert key in context, f"Context should contain {key}"
        
        assert context["file_path"] == "src/main.py", "Context should have correct file path"
        assert context["language"] == "python", "Should detect Python language"
        assert context["file_extension"] == ".py", "Should have correct file extension"
        
        print(f"✓ File context extracted for {context['file_path']}: {context['language']}")
        
        return True
        
    except Exception as e:
        print(f"✗ Additional features test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("Testing refactored DiffParser class...")
    print("=" * 50)
    
    tests = [
        test_import_and_initialization,
        test_simple_diff_parsing,
        test_chunking_functionality,
        test_error_handling,
        test_additional_features
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        else:
            print(f"\n❌ {test.__name__} failed")
            break
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The refactored DiffParser works correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the implementation.")
        return 1

if __name__ == "__main__":
    sys.exit(main())