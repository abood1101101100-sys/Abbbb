import sys

path = sys.argv[1]
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
count = 0
for line in lines:
    if 'await parser(update, users, chats)' in line:
        indent = len(line) - len(line.lstrip())
        sp = ' ' * indent
        new_lines.append(sp + 'try:\n')
        new_lines.append(sp + '    ' + line.lstrip())
        new_lines.append(sp + 'except ValueError as e:\n')
        new_lines.append(sp + '    if "Peer id invalid" not in str(e):\n')
        new_lines.append(sp + '        raise\n')
        count += 1
    else:
        new_lines.append(line)

if count > 0:
    with open(path, 'w') as f:
        f.writelines(new_lines)
    print(f"Patched {count} occurrence(s) successfully")
else:
    print("Pattern not found")
