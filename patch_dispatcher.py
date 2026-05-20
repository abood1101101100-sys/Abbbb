import sys

path = sys.argv[1]
with open(path, 'r') as f:
    lines = f.readlines()

new_lines = []
patched = False
for line in lines:
    if 'await parser(update, users, chats)' in line and not patched:
        indent = len(line) - len(line.lstrip())
        sp = ' ' * indent
        new_lines.append(sp + 'try:\n')
        new_lines.append(sp + '    ' + line.lstrip())  # المسافة + السطر الأصلي
        new_lines.append(sp + 'except ValueError as e:\n')
        new_lines.append(sp + '    if "Peer id invalid" not in str(e):\n')
        new_lines.append(sp + '        raise\n')
        patched = True
        # لا تضف السطر الأصلي مرة ثانية - continue
    else:
        new_lines.append(line)

if patched:
    with open(path, 'w') as f:
        f.writelines(new_lines)
    print("Patched successfully")
else:
    print("Pattern not found")
