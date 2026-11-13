"""[reversing/captive/py/phoopel/panel2/gold.py; run from M68000 as `uv run python -I reversing/captive/py/phoopel/panel2/gold.py <args>`; output under scratchpad/captive/phoopel/panel2/]
(c) pick up a lock-prize GOLD item live. Labelled pokes: party x, y, facing (onto the prize cell E, facing chosen so the
click's corner table $ce24 selects the item's corner = flags & 3). Then a click on the lower part of the view (y >= $98,
$dbb2/$dbd8 -> $c0b8) picks the item at the party's cell into the hand slot 404(A6) (flags, type, word as bytes 0,1,2-3).
usage: gold.py <x,y> [<x,y> ...]    snapshot = base13.snap (D0 = 13)"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
FACE_FOR_CORNER = {0: 0, 2: 1, 3: 2, 1: 3}          # first byte of each $ce24 row: facing -> corner 0, 2, 3, 1
s = StServer(R); s('load', snapshot=SNAP)
base = s('fork')['id']
p = 0x1bf3a; b = s.read(p + 4, 0x800)
items = {}
i = 0
while i + 4 <= len(b):
    x, y, size = b[i], b[i+1], int.from_bytes(b[i+2:i+4], 'big')
    if size < 8 or size > 0x40: break
    items[(x, y)] = [(b[i+4+4*k], int.from_bytes(b[i+5+4*k:i+7+4*k], 'big'), b[i+7+4*k]) for k in range((size - 4) // 4)]
    i += size
def click(x, y):
    for _ in range(3): s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    while x or y:
        mx, my = min(x, 120), min(y, 120); s('mouse', action='move', dx=mx, dy=my); s('step', n=30000); x -= mx; y -= my
    s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l'); s('step', n=200000)
for a in sys.argv[1:]:
    x, y = map(int, a.split(','))
    its = items[(x, y)]; (t, w, fl), = [i for i in its if i[0] == 0x19]
    corner = fl & 3
    s('restore', id=base)
    s('poke', addr=A6 + 26, width=2, value=x); s('poke', addr=A6 + 28, width=2, value=y); s('poke', addr=A6 + 30, width=2, value=FACE_FOR_CORNER[corner])
    s('step', n=180000)
    hand0 = s.read(A6 + 404, 4)
    click(60, 165)       # left half of the view, bottom: facing unchanged ($dbb6-$dbc2)
    hand = s.read(A6 + 404, 4)
    left = items_after = None
    print(f'cell ({x},{y}) listed item: type ${t:02x} word ${w:04x} = {w} flags ${fl:02x} (corner {corner}); hand before {hand0.hex()}, after {hand.hex()} '
          f'-> type ${hand[1]:02x} word {int.from_bytes(hand[2:4], "big")} {"MATCH" if hand[1] == 0x19 and int.from_bytes(hand[2:4], "big") == w else "NO"}')
    for tgt in ('hand',):
        pass
    png = os.path.join(OUT, f'gold_{x}_{y}.png'); s('render', path=png)
s.close()
