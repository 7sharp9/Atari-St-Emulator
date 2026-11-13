"""[reversing/captive/py/phoopel/panel2/scan.py; run from M68000 as `uv run python -I reversing/captive/py/phoopel/panel2/scan.py <args>`; output under scratchpad/captive/phoopel/panel2/]
(a) scan: for lock L of base13.snap, put the party (labelled poke: x, y, facing = W's side) on every open cell within
7 cells ahead of the panel and 3 sideways, let the view redraw, then bp the panel draw ($12a20 entry, the
cmp.w #5,D0 at $12a7e (key kind 3) / $12a92 (kind 2), the two targets) and record D0 at each stop.
usage: scan.py <lock> [facing-override]   output: scratchpad/captive/phoopel/panel2/scan_lock<L>.jsonl and a table on stdout"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
L = int(sys.argv[1])
s = StServer(R); s('load', snapshot=SNAP)
tile = lambda x, y: s.read(TILES + y * 64 + x, 1)[0]
lk = lock_list(s)[L]
wx, wy = lk['W']; face = tile(wx, wy) & 3
f = VEC[face]; side = (-f[1], f[0])
cmpa = 0x12a7e if lk['key'] == 3 else 0x12a92
hit = {0x12a20: 'entry', cmpa: 'cmp5', 0x12a86 if lk['key']==3 else 0x12aac: 'GT5(>5)'}
if lk['key'] == 3: hit[0x12a84] = 'LE5 rts'
else: hit[0x12a98] = 'LE5 pics'
hit[0xab08] = 'orig(open)'; hit[0xab6c] = 'orig(closed)'
s('bp_set', addrs=list(hit))
# labelled poke: the cover bit (bit 2) of W's tile, as the cover click sets it ($ddd2); $12a20 is called only with it set
if os.environ.get('NOCOVER') is None: s('poke', addr=TILES + wy*64 + wx, width=1, value=tile(wx, wy) | 4)
base = s('fork')['id']
rows = []
print(f"lock {L} key {lk['key']} door {lk['door']} W {lk['W']} face {face}")
for d in range(1, 8):
    for lat in (-3, -2, -1, 0, 1, 2, 3):
        x, y = wx - d * f[0] + lat * side[0], wy - d * f[1] + lat * side[1]
        if not (0 <= x < 64 and 0 <= y < 32) or tile(x, y) not in (0x20, 0xa0): continue
        s('restore', id=base)
        s('poke', addr=A6 + 26, width=2, value=x); s('poke', addr=A6 + 28, width=2, value=y); s('poke', addr=A6 + 30, width=2, value=face)
        s('step', n=130000)
        stops = []
        for _ in range(60):
            r = s('run', max_steps=130000)
            if r['reason'] != 'breakpoint': break
            pc = s.reg('pc') & 0xffffff
            stops.append((hit.get(pc, hex(pc)), s.reg('d0') & 0xffff))
        rec = dict(lock=L, depth=d, lat=lat, cell=(x, y), stops=stops)
        rows.append(rec)
        print(f'  depth {d} lat {lat:+d} cell ({x},{y}): ' + ' '.join(f'{n}:{v}' for n, v in dict.fromkeys(stops)))
json.dump(rows, open(os.path.join(OUT, f'scan_lock{L}.jsonl'), 'w'))
s.close()
