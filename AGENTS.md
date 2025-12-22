# AGENTS.md - GLM Code Review Bot for GitLab

## Project Overview
This repository contains a GLM-powered code review bot designed to integrate with GitLab CI/CD. The bot analyzes merge requests using the GLM-4.6 model and posts automated code review comments.

## Current State
- Complete project documentation has been created
- Technical specifications and implementation plans are available
- Ready for implementation phase with clear guidance

## Project Structure
```
/
├── .crush/                    # Crush tool configuration
├── docs/                      # Documentation
│   ├── spec.md               # Project specification (Russian)
│   ├── development_plan.md   # Detailed development roadmap
│   ├── integration_plan.md   # Integration guide
│   └── technical_implementation.md # Technical specifications
├── README.md                 # Project overview and quick start
└── AGENTS.md                 # This file
```

## Project Specification
The project aims to create a bot that:
- Analyzes merge request changes using GLM-4
- Posts structured comments and recommendations in MRs
- Integrates with GitLab CI/CD pipelines
- Processes both small and large code changes
- Supports file-specific, readable comments

## Key Components (To Be Implemented)
1. **GitLab CI/CD Pipeline**: `.gitlab-ci.yml` configuration
2. **Review Bot Script**: Python script (`review_bot.py`) for diff analysis and comment publishing
3. **GLM API Integration**: Interface to GLM-4 model
4. **MR Diff Parser**: Component to process GitLab diffs
5. **Comment Publisher**: Component to post comments via GitLab API

## Environment Variables (Required)
- `GLM_API_KEY`: API key for GLM-4
- `GITLAB_TOKEN`: Personal Access Token for publishing comments
- `GITLAB_API_URL`: GitLab API URL
- `CI_PROJECT_ID`: Project ID in GitLab (auto-provided)
- `CI_MERGE_REQUEST_IID`: MR ID (auto-provided)

## Technical Stack (Planned)
- Language: Python 3.11+
- Dependencies: requests or httpx
- CI/CD: GitLab CI/CD
- Docker: Python 3.11 base image

## Development Guidelines
Implementation should follow the detailed plans outlined in:
- `docs/development_plan.md` - Detailed component breakdown and implementation order
- `docs/integration_plan.md` - Step-by-step integration guide with code examples
- `docs/technical_implementation.md` - In-depth technical specifications and architecture

## Common Commands
This section will be populated with build, test, and run commands as they are added to the project.

## Code Patterns and Conventions
This section will be updated to reflect coding patterns once source code is added.

## Gotchas and Important Notes
This section will be updated with important considerations discovered during implementation.