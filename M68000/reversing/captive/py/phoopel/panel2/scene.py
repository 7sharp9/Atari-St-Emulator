"""[reversing/captive/py/phoopel/panel2/scene.py; run from M68000 as `uv run python -I reversing/captive/py/phoopel/panel2/scene.py <args>`; output under scratchpad/captive/phoopel/panel2/]
(a) renders and per-call draw lists: lock <L> of base13.snap, party poked (labelled) to depth/lateral cells in front of
W (cover bit 2 of W's tile poked as the cover click sets it), the pointer parked top left; renders to
panel2/scene_L<L>_d<depth>_l<lat>.png and the pieces ($b230 D0 at entry) drawn between the $12a20 entry and its return ($ab26).
usage: scene.py <lock> <depth,lat> [<depth,lat> ...]"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
L = int(sys.argv[1]); cells = [tuple(map(int, a.split(','))) for a in sys.argv[2:]]
s = StServer(R); s('load', snapshot=SNAP)
tile = lambda x, y: s.read(TILES + y * 64 + x, 1)[0]
lk = lock_list(s)[L]; wx, wy = lk['W']; face = tile(wx, wy) & 3
f = VEC[face]; side = (-f[1], f[0])
s('poke', addr=TILES + wy*64 + wx, width=1, value=tile(wx, wy) | 4)
if os.environ.get('STATE'):   # labelled poke: the lock record's switch state word (+4), as clicks would set it
    s('poke', addr=LOCKS + 10*L + 4, width=2, value=int(os.environ['STATE'], 16))
SUF = '_st' + os.environ['STATE'] if os.environ.get('STATE') else ''
base = s('fork')['id']
P = {0x12a20: 'ENTRY', 0xb230: 'piece', 0xab26: 'RET', 0x12e5e: 'number', 0x12d46: 'segments/pic-tail', 0x12aac: 'buttons'}
for d, lat in cells:
    x, y = wx - d*f[0] + lat*side[0], wy - d*f[1] + lat*side[1]
    assert tile(x, y) in (0x20, 0xa0), (x, y, tile(x, y))
    s('restore', id=base); s('bp_clear')
    s('poke', addr=A6 + 26, width=2, value=x); s('poke', addr=A6 + 28, width=2, value=y); s('poke', addr=A6 + 30, width=2, value=face)
    s('step', n=130000)
    s('bp_set', addrs=[0x12a20])
    r = s('run', max_steps=200000); assert r['reason'] == 'breakpoint', r
    d0 = s.reg('d0') & 0xffff
    s('bp_clear'); s('bp_set', addrs=list(P))
    seq = []; inside = False
    for _ in range(400):
        r = s('run', max_steps=400000)
        if r['reason'] != 'breakpoint': break
        pc = s.reg('pc') & 0xffffff
        if pc == 0x12a20: inside = True; seq.append('ENTRY'); continue
        if pc == 0xab26 and inside: break
        if inside: seq.append(f"piece ${s.reg('d0') & 0xffff:03x}" if pc == 0xb230 else P[pc])
    s('bp_clear')
    for _ in range(3): s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    s('step', n=140000)
    png = os.path.join(OUT, f'scene_L{L}_d{d}_l{lat}{SUF}.png'); s('render', path=png)
    from collections import Counter
    c = Counter(seq)
    print(f'lock {L} key {lk["key"]} depth {d} lat {lat:+d} cell ({x},{y}) D0={d0}: draws {len(seq)}: ' + ', '.join(seq[:12]) + (' ...' if len(seq) > 12 else ''), '->', png)
s.close()
