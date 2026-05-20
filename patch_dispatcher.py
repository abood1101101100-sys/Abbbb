import sys

path = sys.argv[1]
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
patched = False
while i < len(lines):
    line = lines[i]
    stripped = line.rstrip()
    # Find the exact line with "await parser(update, users, chats)"
    if 'await parser(update, users, chats)' in stripped and not patched:
        indent = len(line) - len(line.lstrip())
        spaces = ' ' * indent
        new_lines.append(spaces + 'try:\n')
        new_lines.append(spaces + '    ' + line.lstrip())
        new_lines.append(spaces + 'except ValueError as e:\n')
        new_lines.append(spaces + '    if "Peer id invalid" not in str(e):\n')
        new_lines.append(spaces + '        raise\n')
        patched = True
    else:
        new_lines.append(line)
    i += 1

if patched:
    with open(path, 'w') as f:
        f.writelines(new_lines)
    print("Patched successfully")
else:
    print("Pattern not found, skipping")
