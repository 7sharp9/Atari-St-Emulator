"""vis_at.py <snap> <camx> <camy> [n]: poke the camera cell ($4bb3a/$4bb3c), let the view re-project, then list the on-screen entities
the draw loop offers to the inspect hit-test $12138 (as ui/visible.py does).  Prints A3, screen (x,y), byte6."""
import re, sys, os
from pathlib import Path
ROOT = Path(os.environ.get('M68000_ROOT') or Path(__file__).resolve().parents[4])
sys.path.insert(0, str(ROOT / 'reversing/powermonger/py/ui'))
from uilib import *
snap = sys.argv[1]; cx, cy = int(sys.argv[2]), int(sys.argv[3]); n = int(sys.argv[4]) if len(sys.argv) > 4 else 200
base = ram_of(snap)
out = repl(snap, [f'w 4bb3a {cx:04x}{cy:04x}', 's 3000000'] + ['bp 12138 400000'] * n)
rows = []; cur = {}
for line in out.splitlines():
    for k, v in re.findall(r'\b([DA][0-7]):([0-9a-f]{8})', line):
        cur[k] = int(v, 16)
    if line.startswith('PC:') and 'A3' in cur:
        rows.append(dict(cur)); cur = {}
seen = {}
for r in rows:
    a = r['A3']; seen.setdefault(a, (r['D0'] & 0xffff, r['D1'] & 0xffff, base[a + 6], base[a + 7]))
for a, (x, y, c, b7) in sorted(seen.items(), key=lambda kv: kv[1][2]):
    print(f'A3=${a:x} screen=({x},{y}) byte6={c:#x} byte7={b7:#x}')
