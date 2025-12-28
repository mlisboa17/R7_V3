from pathlib import Path
s = Path('main.py').read_text(encoding='utf-8')
lines = s.splitlines()
issues = []
for i, line in enumerate(lines):
    if 'try:' in line:
        indent = len(line) - len(line.lstrip())
        found = False
        for j in range(i+1, len(lines)):
            l = lines[j]
            if not l.strip():
                continue
            jindent = len(l) - len(l.lstrip())
            # look for except/finally at same indentation
            if jindent == indent and (l.lstrip().startswith('except') or l.lstrip().startswith('finally')):
                found = True
                break
            # if dedent below indent and no except/finally found, break
            if jindent < indent:
                break
        if not found:
            issues.append((i+1, line))
if not issues:
    print('No unmatched try: blocks found by heuristic')
else:
    print('Unmatched try: blocks (heuristic):')
    for ln, text in issues:
        print(ln, text)
