with open('src/url/gui_app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()
print(f'Total lines: {len(lines)}')
with open('_find_result.txt', 'w', encoding='utf-8') as out:
    out.write(f'Total lines: {len(lines)}\n')
    for i, line in enumerate(lines, 1):
        if 'offline' in line.lower():
            out.write(f'{i}: {line.rstrip()}\n')
        if '\u79bb\u7ebf' in line:
            out.write(f'{i}: [CN] {line.rstrip()}\n')
    # Also check: any def methods related to crawl after line 1680
    out.write('\n--- All def methods after L1680 ---\n')
    for i, line in enumerate(lines, 1):
        if i > 1680 and 'def ' in line and ('crawl' in line.lower() or 'insert' in line.lower()):
            out.write(f'{i}: {line.rstrip()}\n')
