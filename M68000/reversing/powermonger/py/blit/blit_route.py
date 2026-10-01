"""Routing check for blit_gate.py: the callcap step count of each case is steps = c + r * rows_drawn with (c, r) fixed per clip routine.
Prints the per-row step cost and the overhead spread per clip routine: a distinct slope per variant (and a narrow overhead) shows the
label is the routine that ran. Needs blit_gate.py's callcap outputs (run it first)."""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import blit_gate as G
res = {}
for name, entry, a1, x, y, rows, wide in G.cases():
    v = G.variant(x, y, rows, wide)
    if v is None: continue
    j = json.load(open(G.OUT / f"o_{name}.json"))
    ys = max(y, 0); ye = min(y + rows, 200); drawn = ye - ys
    res.setdefault((name[:3], v), []).append((drawn, j["steps"]))
for k, pts in sorted(res.items(), key=str):
    by = {}
    for d, s in pts: by.setdefault(d, set()).add(s)
    ds = sorted(by)
    if len(ds) < 2: print(k, "single row count", ds); continue
    r = (min(by[ds[-1]]) - min(by[ds[0]])) / (ds[-1] - ds[0])
    cs = [s - r * d for d, ss in by.items() for s in ss]
    print(f"{k[0]} {k[1]:18} {r:.0f} steps per drawn row, entry/clip overhead {min(cs):.0f}..{max(cs):.0f}, {len(cs)} cases")
