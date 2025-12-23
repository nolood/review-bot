import re

PLUS_LINE_PATTERN = re.compile(r'^\s*\+')
MINUS_LINE_PATTERN = re.compile(r'^\s*-')

test_lines = [
    '@@ -1,5 +1,7 @@',
    ' def hello_world():',
    ' -    print("Hello, World!")',
    ' +    print("Hello, Enhanced World!")',
    ' +    # Added a comment',
    ' +    return True',
    ' ',
    ' if __name__ == "__main__":',
    ''
]

added_lines = 0
removed_lines = 0

for line in test_lines:
    print(f"Line: {repr(line)}")
    plus_match = PLUS_LINE_PATTERN.match(line)
    minus_match = MINUS_LINE_PATTERN.match(line)
    print(f"  PLUS_LINE_PATTERN.match: {plus_match is not None}")
    print(f"  MINUS_LINE_PATTERN.match: {minus_match is not None}")
    
    if plus_match and not line.startswith('+++'):
        added_lines += 1
        print(f"  -> COUNTED as added line")
    elif minus_match and not line.startswith('---'):
        removed_lines += 1
        print(f"  -> COUNTED as removed line")
    else:
        print(f"  -> NOT counted")
    print()

print(f"Total added lines: {added_lines}")
print(f"Total removed lines: {removed_lines}")
