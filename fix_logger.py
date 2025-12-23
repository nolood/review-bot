#!/usr/bin/env python3
import re

# Read the logger file
with open('src/utils/logger.py', 'r') as f:
    content = f.read()

# Replace settings usages with safe access
content = re.sub(
    r'if settings\.project_id:',
    'if settings and settings.project_id:',
    content
)

content = re.sub(
    r'if settings\.mr_iid:',
    'if settings and settings.mr_iid:',
    content
)

content = re.sub(
    r'record\.project_id = settings\.project_id',
    'record.project_id = settings.project_id if settings else None',
    content
)

content = re.sub(
    r'record\.mr_iid = settings\.mr_iid',
    'record.mr_iid = settings.mr_iid if settings else None',
    content
)

# For the settings usage in setup_logging function
content = re.sub(
    r'level_str = str\(level\) if level else settings\.log_level',
    '''level_str = str(level) if level else (settings.log_level if settings else "INFO")''',
    content
)

content = re.sub(
    r'format_str = str\(format_type\) if format_type else settings\.log_format',
    '''format_str = str(format_type) if format_type else (settings.log_format if settings else "text")''',
    content
)

content = re.sub(
    r'log_file_path = log_file or settings\.log_file',
    '''log_file_path = log_file or (settings.log_file if settings else None)''',
    content
)

# Write back
with open('src/utils/logger.py', 'w') as f:
    f.write(content)

print("Fixed logger.py settings usages")
