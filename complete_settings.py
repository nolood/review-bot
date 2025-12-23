class MockSettings:
    def __init__(self):
        # Diff parsing settings
        self.max_diff_size = 1000
        
        # Logging settings
        self.log_level = "INFO"
        self.log_format = "text"
        self.log_file = None
        
        # GitLab context settings for logging
        self.project_id = None
        self.mr_iid = None
        
        # GitLab client settings
        self.gitlab_token = "test_token"
        self.gitlab_api_url = "https://gitlab.example.com/api/v4"
        
        # GLM client settings
        self.glm_api_key = "test_glm_api_key"
        self.glm_api_url = "https://api.example.com/v1/chat/completions"
        
        # File filtering settings
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
