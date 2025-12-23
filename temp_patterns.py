import re
# New patterns
HUNK_HEADER_PATTERN = re.compile(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@')
PLUS_LINE_PATTERN = re.compile(r'^\s*\+')
MINUS_LINE_PATTERN = re.compile(r'^\s*-')
CONTEXT_LINE_PATTERN = re.compile(r'^ ')

print("Patterns updated")
