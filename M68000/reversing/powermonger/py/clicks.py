"""clicks.py <x,y|cmd> ... -> REPL commands. Homes the pointer to (0,0), then moves 1:1 to each
absolute (x,y) and clicks there (README trap: down / move 0 0 / s 300000 / up / move 0 0).
`home` re-homes the pointer. A token that is not x,y is passed through as a raw REPL command (use : for spaces)."""
import sys
HOME = ["mouse move -400 -400", "s 300000", "mouse move 0 0", "s 300000"]
out = list(HOME)
px = py = 0
for t in sys.argv[1:]:
    if t == 'home':
        out += HOME; px = py = 0; continue
    if ',' in t and t.replace(',', '').replace('-', '').isdigit():
        x, y = map(int, t.split(','))
        out += [f"mouse move {x-px} {y-py}", "s 300000", "mouse move 0 0", "s 300000",
                "mouse down l", "mouse move 0 0", "s 300000", "mouse up l", "mouse move 0 0", "s 300000"]
        px, py = x, y
    else:
        out.append(t.replace(':', ' '))
print('\n'.join(out))
