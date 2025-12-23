class MockSettings:
    def __init__(self):
        self.max_diff_size = 1000  # Default fallback
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
        import fnmatch
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.ignore_file_patterns)
    
    def is_file_prioritized(self, file_path: str) -> bool:
        """Check if a file should be prioritized based on patterns."""
        import fnmatch
        return any(fnmatch.fnmatch(file_path, pattern) for pattern in self.prioritize_file_patterns)

# Replace settings None with MockSettings instance
settings = MockSettings()
