import sys

path = sys.argv[1]
with open(path, 'r') as f:
    content = f.read()

old = '''                parsed_update, handler_type = (
                    await parser(update, users, chats)
                    if parser is not None
                    else (None, type(None))
                )'''

new = '''                if parser is not None:
                    try:
                        parsed_update, handler_type = await parser(update, users, chats)
                    except ValueError as e:
                        if "Peer id invalid" not in str(e):
                            raise
                        continue
                else:
                    parsed_update, handler_type = (None, type(None))'''

if old in content:
    content = content.replace(old, new)
    with open(path, 'w') as f:
        f.write(content)
    print("Patched successfully")
else:
    print("Pattern not found")
    # Debug
    for i, line in enumerate(content.splitlines()[338:348], start=339):
        print(f"{i}: {repr(line)}")
