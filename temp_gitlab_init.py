        # Always use environment variables
        self.token = os.getenv("GITLAB_TOKEN", "")
        self.api_url = os.getenv("GITLAB_API_URL", "https://gitlab.com/api/v4")
        self.project_id = os.getenv("CI_PROJECT_ID", "")
        self.mr_iid = os.getenv("CI_MERGE_REQUEST_IID", "")
        
        # Set fallback settings for logging and other components
        if not hasattr(settings, 'project_id'):
            settings.project_id = self.project_id
            settings.mr_iid = self.mr_iid
