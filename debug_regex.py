import re

PLUS_LINE_PATTERN = re.compile(r'^\+')
MINUS_LINE_PATTERN = re.compile(r'^-')

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
    print(f"  Starts with '+': {line.startswith('+')}")
    print(f"  Starts with '+++: {line.startswith('+++')}")
    print(f"  PLUS_LINE_PATTERN.match: {PLUS_LINE_PATTERN.match(line) is not None}")
    print(f"  Condition passes: {PLUS_LINE_PATTERN.match(line) and not line.startswith('+++')}")
    
    if PLUS_LINE_PATTERN.match(line) and not line.startswith('+++'):
        added_lines += 1
        print(f"  -> COUNTED as added line")
    elif MINUS_LINE_PATTERN.match(line) and not line.startswith('---'):
        removed_lines += 1
        print(f"  -> COUNTED as removed line")
    else:
        print(f"  -> NOT counted")
    print()

print(f"Total added lines: {added_lines}")
print(f"Total removed lines: {removed_lines}")
