import re

PLUS_LINE_PATTERN = re.compile(r'^\+')
MINUS_LINE_PATTERN = re.compile(r'^-')

# These are the exact lines from the debug output
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

for i, line in enumerate(test_lines):
    print(f"Line {i}: {repr(line)}")
    print(f"  Character codes: {[ord(c) for c in line[:3] if c != ' ']}")
    if line.strip():
        first_char = line.strip()[0]
        print(f"  First non-space char: {repr(first_char)}")
    print()
