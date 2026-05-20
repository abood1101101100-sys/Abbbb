import sys

path = sys.argv[1]
with open(path, 'r') as f:
    lines = f.readlines()

# Print lines around 340-345 for debugging
print("=== Lines 338-346 ===")
for i, line in enumerate(lines[337:346], start=338):
    print(f"{i}: {repr(line)}")

print("=== All lines with 'await parser' ===")
for i, line in enumerate(lines, start=1):
    if 'await parser' in line:
        print(f"{i}: {repr(line)}")

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
