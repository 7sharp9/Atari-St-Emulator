"""What finishes a base, driven in the D0 = 13 base (base13.snap): EXPLOSIVES on a generator.

Labelled pokes: the party's x, y, facing (fed 26/28/30(A6)) to stand beside a generator cell (tile $28) facing it,
and the hand slot 404(A6) = $801b0000 (item $1b, EXPLOSIVES). Then one click in the view at (100,105) ($deb4).
Samples the base-state words 13406/13408/13410(A6), 14800(A6) and the count of tiles $28/$29 and $26/$27 every
60,000 steps and prints each change. Arms:
  blast     hand = EXPLOSIVES: 13410 goes 1 -> 2 -> 3
  control   hand = empty (0): 13410 stays 0
The blast arm also follows the fire cell 13406(A6) against the dig arrows (plane 2 bits 0-2, read before the click)
and saves <TAG>_blast_state2.snap at the first state-2 sample, the start state for leave.py.
Usage: [SNAP=<snap under scratchpad/captive> TAG=<output prefix>] finish13.py [gx gy]
default: base13.snap, the first tile-$28 cell with an open neighbour"""
import os, sys
_M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/ai')
from cap import R, StServer, A6, W  # noqa: E402

OUTD = os.path.join(W, 'phoopel')
s = StServer(R)
SNAP = os.environ.get('SNAP', os.path.join(OUTD, 'base13.snap'))
TAG = os.environ.get('TAG', 'finish')
s('load', snapshot=SNAP if os.path.isabs(SNAP) else os.path.join(W, SNAP))

w = lambda off: int.from_bytes(s.read(A6 + off, 2), 'big')
tiles = lambda: s.read(A6 + 9242, 2048)
T = tiles()
VEC = ((0, -1), (-1, 0), (0, 1), (1, 0))  # facing 0 N, 1 W, 2 S, 3 E
gens = [(i % 64, i // 64) for i in range(2048) if T[i] & 0x7e == 0x28]
print('generator tiles ($28/$29):', gens)
if len(sys.argv) > 2:
    cand = [(int(sys.argv[1]), int(sys.argv[2]))]
else:
    cand = gens
for gx, gy in cand:
    spot = [(gx - dx, gy - dy, f) for f, (dx, dy) in enumerate(VEC)
            if 0 <= gx - dx < 64 and 0 <= gy - dy < 32 and T[(gy - dy) * 64 + gx - dx] & 0x7f in (0x20, 0x21)]
    if spot:
        break
px, py, face = spot[0]
ent = (w(22), w(24))
print(f'generator ({gx},{gy}); labelled pokes: party ({px},{py}) facing {face}; entrance words 22/24(A6) = {ent}')
base = s('fork')['id']


def state(tag):
    t = tiles()
    print(f'  {tag}: 13410={w(13410)} 13408={w(13408)} 13406=${w(13406):04x} 14800={w(14800)} mode={w(13564)} '
          f'visited={w(14794)} tiles $28/$29: {sum(b & 0x7e == 0x28 for b in t)} $26/$27: {sum(b & 0x7e == 0x26 for b in t)}')


def click(x, y):
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    while x or y:
        mx, my = min(x, 120), min(y, 120)
        s('mouse', action='move', dx=mx, dy=my); s('step', n=30000); x -= mx; y -= my
    s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l'); s('step', n=120000)


for name, hand in (('blast', 0x801b0000), ('control', 0)):
    s('restore', id=base)
    for off, v in ((26, px), (28, py), (30, face)):
        s('poke', addr=A6 + off, width=2, value=v)
    s('poke', addr=A6 + 404, width=4, value=hand)
    s('step', n=180000)
    print(f'arm {name}: hand 404(A6) = ${hand:08x}, cell ahead 15408(A6) = ${s.read(A6 + 15408, 1)[0]:02x}')
    s('render', path=os.path.join(OUTD, f'{TAG}_{name}_before.png'))
    state('before click')
    click(100, 105)
    state('after click')
    p2 = s.read(A6 + 11322, 2048)          # plane 2 before the fire: bits 0-2 are the dig arrows
    last, path, n, limit = None, [], 0, (60_000_000 if hand else 6_000_000)
    while n < limit and w(13410) != 3:
        s('step', n=60000); n += 60000
        cur = (w(13410), w(13406))
        if cur != last:
            if cur[0] == 2 and (last is None or last[0] != 2):
                s('save', path=os.path.join(OUTD, f'{TAG}_{name}_state2.snap'))
            if cur[0] == 2:
                path.append((cur[1] >> 8, cur[1] & 255))
            state(f'+{n:9d} steps, fire cell ({cur[1] >> 8},{cur[1] & 255})')
            last = cur
    moves = [VEC.index((d[0] - c[0], d[1] - c[1])) if (d[0] - c[0], d[1] - c[1]) in VEC else -1
             for c, d in zip(path, path[1:])]
    ok = sum(m == p2[c[1] * 64 + c[0]] & 7 for m, c in zip(moves, path))
    print(f'  fire path {path[:1]} .. {path[-1:]}: {ok}/{len(moves)} moves equal bits 0-2 of the cell left; '
          f'entrance {ent} reached: {ent in path}')
    s('render', path=os.path.join(OUTD, f'{TAG}_{name}_after.png'))
s.close()
