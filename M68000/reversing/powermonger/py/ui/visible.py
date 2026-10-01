"""List the on-screen entities the draw loop offers to the inspect hit-test ($12138: D0=x D1=y, A3=record).
python visible.py <snap> [n=150]"""
import re, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from uilib import *
snap = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 150
base = ram_of(snap)
out = repl(snap, ['bp 12138 400000'] * n)
rows = []; cur = {}
for line in out.splitlines():
    for k, v in re.findall(r'\b([DA][0-7]):([0-9a-f]{8})', line):
        cur[k] = int(v, 16)
    if line.startswith('PC:') and 'A3' in cur:
        rows.append(dict(cur)); cur = {}
seen = {}
for r in rows:
    a = r['A3']
    seen.setdefault(a, (r['D0'] & 0xffff, r['D1'] & 0xffff, base[a + 6], base[a + 7]))
for a, (x, y, c, b7) in sorted(seen.items(), key=lambda kv: kv[1][2]):
    print(f'A3=${a:x} screen=({x},{y}) byte6={c:#x} byte7={b7:#x}')
