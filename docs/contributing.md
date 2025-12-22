# Contributing Guidelines

## Overview

We welcome contributions to the GLM Code Review Bot project! This guide covers how to contribute effectively, including development setup, coding standards, and pull request process.

## Getting Started

### Fork and Clone

1. Fork the repository on GitLab
2. Clone your fork locally:
```bash
git clone https://gitlab.com/your-username/review-bot.git
cd review-bot
```

3. Add upstream remote:
```bash
git remote add upstream https://gitlab.com/original-project/review-bot.git
```

### Development Setup

1. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

3. Set up pre-commit hooks:
```bash
pre-commit install
```

4. Copy environment file:
```bash
cp .env.example .env
# Add your test tokens for development
```

## Development Workflow

### 1. Create Feature Branch

```bash
# Update from upstream
git fetch upstream
git checkout -b feature/your-feature-name upstream/main

# Or for bug fixes
git checkout -b fix/issue-description upstream/main
```

### 2. Development Process

Follow these practices during development:

- **Small, focused commits**: Each commit should address one issue
- **Test as you go**: Run tests frequently
- **Document changes**: Update docstrings and comments
- **Follow style guide**: Use the configured formatters

### 3. Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_glm_client.py

# Run with debug output
pytest -v -s tests/
```

### 4. Code Quality Checks

```bash
# Format code
black src/ tests/
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/
```

## Coding Standards

### Python Style

We follow:
- **PEP 8** with some extensions (120 character line length)
- **Black** for code formatting
- **isort** for import sorting
- **Type hints** for all public functions

### Code Structure

Follow the existing module structure:

```
src/
├── config/          # Configuration management
├── utils/           # Utility modules
├── gitlab_client.py  # GitLab API client
├── glm_client.py     # GLM API client
├── diff_parser.py    # Diff processing
├── comment_publisher.py  # Comment handling
└── __init__.py
```

### Naming Conventions

- **Classes**: PascalCase (`GitLabClient`, `DiffParser`)
- **Functions**: snake_case (`parse_gitlab_diff`, `analyze_code`)
- **Constants**: UPPER_SNAKE_CASE (`MAX_DIFF_SIZE`, `API_URL`)
- **Private**: Single underscore (`_internal_method`)

### Documentation

- **Docstrings**: Use Google style for all public functions
- **Comments**: Explain "why" not "what"
- **README**: Update with new features
- **Examples**: Include usage examples in docstrings

### Example Docstring

```python
def analyze_code(
    diff_content: str,
    review_type: ReviewType = ReviewType.GENERAL,
    custom_prompt: Optional[str] = None
) -> Dict[str, Any]:
    """Analyze code changes using GLM-4 model.
    
    Args:
        diff_content: Git diff content to analyze
        review_type: Type of review to perform
        custom_prompt: Optional custom instructions
        
    Returns:
        Dictionary containing analysis results and comments
        
    Raises:
        GLMAPIError: If API call fails
        ValueError: If diff content is invalid
        
    Example:
        >>> result = analyze_code("diff content", ReviewType.SECURITY)
        >>> print(result['comments'])
        [{'file': 'app.py', 'line': 42, 'comment': '...'}]
    """
```

## Testing Guidelines

### Test Structure

Follow the existing test structure:

```
tests/
├── conftest.py          # Shared fixtures and configuration
├── fixtures.py          # Test data and mock responses
├── unit/               # Unit tests for individual components
├── integration/        # Integration tests for component interaction
└── test_*.py           # Individual test files
```

### Writing Tests

1. **Test Public Interfaces**: Test what users interact with
2. **Use Fixtures**: Reuse test setup and data
3. **Mock External Services**: Don't call real APIs in tests
4. **Test Error Cases**: Verify proper error handling

### Example Test

```python
def test_glm_client_analyze_code_success(mocker):
    """Test successful code analysis."""
    # Setup
    mock_response = {
        "choices": [{
            "message": {
                "content": '{"comments": [{"file": "test.py", "comment": "Good code"}]}'
            }
        }],
        "usage": {"total_tokens": 100}
    }
    
    mock_post = mocker.patch('httpx.Client.post')
    mock_post.return_value.json.return_value = mock_response
    
    client = GLMClient(api_key="test-key")
    
    # Execute
    result = client.analyze_code("test diff")
    
    # Verify
    assert "comments" in result
    assert len(result["comments"]) == 1
    assert result["comments"][0]["file"] == "test.py"
```

### Coverage Requirements

- **New code**: 90%+ test coverage
- **Critical paths**: 100% test coverage
- **Error handling**: All error paths tested

## Pull Request Process

### 1. Before Submitting

1. **Run all tests**:
```bash
pytest --cov=src
```

2. **Check code quality**:
```bash
black --check src/ tests/
flake8 src/ tests/
mypy src/
```

3. **Update documentation**:
   - README.md for user-facing changes
   - API documentation for new endpoints
   - Changelog for user-visible changes

4. **Clean commit history**:
   - Squash related commits
   - Clear commit messages
   - No merge commits

### 2. Submitting PR

1. **Push to your fork**:
```bash
git push origin feature/your-feature-name
```

2. **Create MR in GitLab**:
   - Target: `main` branch
   - Title: Clear and descriptive
   - Description: Include what and why

3. **Fill MR template**:
   - Type of change (feature/bugfix/docs)
   - Testing done
   - Breaking changes
   - Related issues

### 3. MR Description Template

```markdown
## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation
- [ ] Refactoring
- [ ] Performance improvement
- [ ] Other

## Description
Brief description of changes and their purpose.

## Testing
- [ ] Unit tests pass
- [ ] Integration tests pass
- [ ] Manual testing completed
- [ ] Edge cases considered

## Checklist
- [ ] Code follows style guidelines
- [ ] Self-review completed
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Breaking changes documented
```

## Development Areas

### Core Components

1. **GLM Client** (`src/glm_client.py`)
   - API integration
   - Prompt engineering
   - Response parsing
   - Token management

2. **GitLab Client** (`src/gitlab_client.py`)
   - API authentication
   - Diff fetching
   - Comment publishing
   - Error handling

3. **Diff Parser** (`src/diff_parser.py`)
   - Diff processing
   - File filtering
   - Chunking logic
   - Token estimation

4. **Comment Publisher** (`src/comment_publisher.py`)
   - Comment formatting
   - Markdown rendering
   - Rate limiting
   - Inline comments

### Extending the Bot

#### Adding New Review Types

1. **Update ReviewType enum**:
```python
# src/config/prompts.py
class ReviewType(str, Enum):
    GENERAL = "general"
    SECURITY = "security"
    PERFORMANCE = "performance"
    ACCESSIBILITY = "accessibility"  # New type
```

2. **Add prompt template**:
```python
ACCESSIBILITY_FOCUSED_PROMPT = """You are an accessibility expert...
Focus on:
- Screen reader compatibility
- Keyboard navigation
- Color contrast
- Alternative text
"""
```

3. **Update get_system_prompt**:
```python
def get_system_prompt(review_type: ReviewType) -> str:
    if review_type == ReviewType.ACCESSIBILITY:
        return ACCESSIBILITY_FOCUSED_PROMPT
    # ... other types
```

4. **Add tests**:
```python
def test_accessibility_review():
    prompt = get_system_prompt(ReviewType.ACCESSIBILITY)
    assert "accessibility" in prompt.lower()
```

#### Adding New API Integrations

1. **Create new client**:
```python
# src/new_client.py
class NewAPIClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
    
    def analyze(self, content: str) -> Dict:
        # Implementation
        pass
```

2. **Add configuration**:
```python
# src/config/settings.py
@dataclass
class Settings:
    new_api_key: str = field(default_factory=lambda: os.getenv("NEW_API_KEY"))
    new_api_url: str = "https://api.example.com/v1"
```

3. **Integrate with main flow**:
```python
# review_bot.py
def _initialize_clients(self):
    if settings.use_new_api:
        analyzer = NewAPIClient(settings.new_api_key)
    else:
        analyzer = GLMClient(settings.glm_api_key)
```

## Community Guidelines

### Code of Conduct

- **Be respectful**: Treat all contributors with respect
- **Be constructive**: Provide helpful, actionable feedback
- **Be inclusive**: Welcome contributors of all backgrounds
- **Be patient**: Not everyone has the same experience level

### Communication Channels

- **Issues**: For bugs and feature requests
- **Merge Requests**: For code contributions
- **Discussions**: For questions and ideas
- **Email**: For security issues only

### Getting Help

1. **Check documentation**:
   - README.md
   - API documentation
   - Existing issues

2. **Ask questions**:
   - Start a discussion
   - Comment on related issues
   - Contact maintainers

3. **Report issues**:
   - Use issue templates
   - Provide complete information
   - Include logs and screenshots

## Release Process

### Version Management

We follow Semantic Versioning:
- **Major**: Breaking changes
- **Minor**: New features (backward compatible)
- **Patch**: Bug fixes (backward compatible)

### Release Checklist

1. **Update version** in `src/config/settings.py`
2. **Update CHANGELOG.md** with changes
3. **Tag release** in Git
4. **Create GitLab release** with notes
5. **Update documentation** if needed

## Security

### Reporting Vulnerabilities

For security issues:
1. **Email**: security@project.com
2. **Private issue**: Use GitLab's private issue feature
3. **Include**: Steps to reproduce, impact, and version

### Security Practices

- **No secrets in code**: Use environment variables
- **Input validation**: Sanitize all inputs
- **HTTPS only**: All API calls over HTTPS
- **Principle of least privilege**: Minimal token scopes

## License

By contributing, you agree that your contributions will be licensed under the project's license (MIT License).

## Recognition

Contributors are recognized in:
- **CONTRIBUTORS.md**: List of all contributors
- **Release notes**: Specific contributions
- **GitLab**: Credit in commit history

Thank you for contributing to GLM Code Review Bot! 🚀