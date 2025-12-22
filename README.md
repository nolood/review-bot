# GLM Code Review Bot for GitLab

An automated code review bot that integrates with GitLab CI/CD to provide intelligent code analysis using the GLM-4 model. The bot analyzes merge requests and posts structured comments directly in the MR, helping developers improve code quality.

## Features

- 🔍 **Intelligent Code Analysis** - Uses GLM-4 model for comprehensive code review
- 📝 **File-Specific Comments** - Provides targeted feedback with line references
- 🚀 **GitLab CI/CD Integration** - Seamlessly integrates into your existing pipeline
- 📊 **Multi-File Support** - Handles both small and large merge requests
- 🎯 **Configurable Reviews** - Customizable review criteria and severity levels
- 🔐 **Security Focus** - Identifies potential security vulnerabilities
- ⚡ **Performance Optimized** - Efficient diff processing and chunking

## Quick Start

### 1. Prerequisites

- GitLab project with CI/CD enabled
- GitLab Personal Access Token with `api` scope
- GLM API key from [Z.ai](https://z.ai/)

### 2. Setup

1. Clone this repository to your GitLab project
2. Set up the following CI/CD variables in GitLab:

   | Variable | Description | Protected | Masked |
   |----------|-------------|-----------|--------|
   | `GLM_API_KEY` | Your GLM API key | Yes | Yes |
   | `GITLAB_TOKEN` | GitLab Personal Access Token | Yes | Yes |
   | `GITLAB_API_URL` | GitLab API URL | No | No |

3. Add the following to your `.gitlab-ci.yml`:

```yaml
stages:
  - review

code_review:
  stage: review
  image: python:3.11
  variables:
    PYTHON_VERSION: "3.11"
  before_script:
    - pip install -r requirements.txt
  script:
    - python review_bot.py
  only:
    - merge_requests
  artifacts:
    paths:
      - review_logs/
    expire_in: 1 week
  rules:
    - if: '$CI_PIPELINE_SOURCE == "merge_request_event"'
```

### 3. Configuration

Optional configuration via CI/CD variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `GLM_TEMPERATURE` | 0.3 | GLM model creativity (0-1) |
| `MAX_DIFF_SIZE` | 50000 | Maximum diff size in tokens |
| `ENABLE_SECURITY_REVIEW` | true | Enable security analysis |
| `ENABLE_PERFORMANCE_REVIEW` | true | Enable performance analysis |
| `MIN_SEVERITY_LEVEL` | low | Minimum comment severity |

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitLab CI     │    │  Review Bot     │    │   GLM API       │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │   Pipeline  │ │    │ │ Diff Parser │ │    │ │   Analysis  │ │
│ │   Trigger   ├─┼───▶│ │             ├─┼───▶│ │   Engine    │ │
│ └─────────────┘ │    │ └─────────────┘ │    │ └─────────────┘ │
│                 │    │                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ Comment     │ │◀───│ │ Comment     │ │    │                 │
│ │ Publisher   │ │    │ │ Publisher   │ │    │                 │
│ └─────────────┘ │    │ └─────────────┘ │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## Documentation

- [Development Plan](docs/development_plan.md) - Detailed implementation roadmap
- [Integration Guide](docs/integration_plan.md) - Step-by-step integration instructions
- [Technical Specification](docs/technical_implementation.md) - In-depth technical details
- [Project Specification](docs/spec.md) - Original project requirements (Russian)

## Example Output

The bot generates structured comments like this:

### 📁 src/calculator.py

💡 (line 13): Consider using type hints for better code documentation
⚠️ (line 25): Division by zero possible - add input validation
🚨 (line 42): Hardcoded credentials detected - use environment variables

### 📊 Overall Review Summary

- **Security**: 2 high-severity issues found
- **Performance**: 1 optimization opportunity identified
- **Code Quality**: 3 suggestions for improvement
- **Documentation**: 1 missing docstring detected

## File Structure

```
/
├── .gitlab-ci.yml          # CI/CD pipeline configuration
├── requirements.txt        # Python dependencies
├── review_bot.py          # Main bot script
├── src/
│   ├── gitlab_client.py   # GitLab API client
│   ├── glm_client.py      # GLM API client
│   ├── diff_parser.py     # Diff processing
│   └── comment_publisher.py # Comment formatting
├── tests/                 # Test suite
├── config/                # Configuration files
└── docs/                  # Documentation
```

## Customization

### Custom Review Rules

Create a `config/review_rules.py` file to define custom rules:

```python
CUSTOM_RULES = {
    'python': {
        'naming': {
            'pattern': r'^[a-z_][a-z0-9_]*$',
            'message': 'Variable names should follow snake_case convention'
        }
    }
}
```

### Custom Prompts

Override default prompts in `config/prompts.py`:

```python
SYSTEM_PROMPT = """
You are a senior code reviewer with expertise in:
- Clean code principles
- Design patterns
- Performance optimization
- Security best practices

Focus on actionable, specific feedback.
"""
```

## Troubleshooting

### Common Issues

1. **GLM API Errors**
   - Verify your API key is correct
   - Check if you've exceeded rate limits
   - Ensure API endpoint is accessible from GitLab runners

2. **GitLab Permission Errors**
   - Verify your token has the `api` scope
   - Check if the user has sufficient permissions
   - Ensure CI/CD variables are properly configured

3. **Large Merge Requests**
   - The bot automatically chunks large diffs
   - Processing time increases with diff size
   - Consider enabling `MAX_DIFF_SIZE` limit

### Debug Mode

Enable debug logging by setting `LOG_LEVEL=debug` in your CI/CD variables:

```yaml
variables:
  LOG_LEVEL: "debug"
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a merge request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues and questions:
- Create an issue in this repository
- Check the [troubleshooting guide](#troubleshooting)
- Review the [documentation](docs/)

## Roadmap

- [ ] Support for additional Git platforms (GitHub, Bitbucket)
- [ ] Web dashboard for review analytics
- [ ] Custom rule editor
- [ ] Integration with popular IDEs
- [ ] Multi-language model support

---

Made with ❤️ by the GLM Code Review Bot team