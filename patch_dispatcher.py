import re, sys

path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

old = '                await parser(update, users, chats)'
new = '''                try:
                    await parser(update, users, chats)
                except ValueError as e:
                    if "Peer id invalid" not in str(e):
                        raise'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Pattern not found, skipping")
