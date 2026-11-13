"""[reversing/captive/py/phoopel/panel2/gold_stack.py; run from M68000 as `uv run python -I reversing/captive/py/phoopel/panel2/gold_stack.py <args>`; output under scratchpad/captive/phoopel/panel2/]
(c) GOLD amount and the stack rule $e7d0. Three lock-prize GOLD items of base13.snap are picked up live (labelled pokes of
party cell/facing, then a click on the lower view; as gold.py), each time the hand is put into / swapped with a droid pocket by
calling federation's own $e7d0 (the pocket-click handler body, A0 = pocket; a scratch slot at $7f000) instead of clicking the inventory screen
(labelled: routine call, not a click). Predicted: pocket swap, then both GOLD -> pocket cleared and hand word = sum
(or, above $ffdc, pocket = sum - $ffdc and hand = $ffdc).
usage: gold_stack.py <x,y> <x,y> <x,y> ...   output: hand and pocket words after each step"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import *
FACE = {0: 0, 2: 1, 3: 2, 1: 3}
s = StServer(R); s('load', snapshot=SNAP)
rd = lambda a, n: s.read(a, n)
b = rd(0x1bf3a + 4, 0x800); items = {}; i = 0
while i + 4 <= len(b):
    x, y, size = b[i], b[i+1], int.from_bytes(b[i+2:i+4], 'big')
    if size < 8 or size > 0x40: break
    items[(x, y)] = [(b[i+4+4*k], int.from_bytes(b[i+5+4*k:i+7+4*k], 'big'), b[i+7+4*k]) for k in range((size - 4) // 4)]; i += size
pocket = 0x7f000   # scratch RAM (394(A6) is 0 here: no droid inventory is open), labelled: a stand-in pocket slot, zeroed
s('poke', addr=pocket, width=4, value=0)
print(f'pocket = ${pocket:06x}: {rd(pocket, 4).hex()}; hand {rd(A6 + 404, 4).hex()}')
def click(x, y):
    for _ in range(3): s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    while x or y:
        mx, my = min(x, 120), min(y, 120); s('mouse', action='move', dx=mx, dy=my); s('step', n=30000); x -= mx; y -= my
    s('mouse', action='down', button='l'); s('step', n=60000); s('mouse', action='up', button='l'); s('step', n=200000)
word = lambda a: int.from_bytes(rd(a + 2, 2), 'big')
def state(tag):
    h, p = rd(A6 + 404, 4), rd(pocket, 4)
    print(f'  {tag:34s} hand type ${h[1]:02x} word {word(A6 + 404):5d} | pocket0 type ${p[1]:02x} word {word(pocket):5d}')
    return word(A6 + 404) if h[1] == 0x19 else 0, word(pocket) if p[1] == 0x19 else 0
total = 0; held = 0
for a in sys.argv[1:]:
    x, y = map(int, a.split(','))
    (t, w, fl), = [i for i in items[(x, y)] if i[0] == 0x19]
    s('poke', addr=A6 + 26, width=2, value=x); s('poke', addr=A6 + 28, width=2, value=y); s('poke', addr=A6 + 30, width=2, value=FACE[fl & 3])
    s('step', n=180000)
    if rd(A6 + 405, 1)[0]:                       # hand holds the previous stack: park it in the (empty) pocket first
        s.call_resume(0xe7d0, a0=pocket); state('hand parked in pocket0 ($e7d0)')
    click(60, 165); h = state(f'picked up ({x},{y}) listed word {w}')
    assert word(A6 + 404) == w, 'hand word != listed word'
    s.call_resume(0xe7d0, a0=pocket)
    h, p = state('$e7d0 with pocket0 holding the stack')
    total += w
    print(f'     listed sum so far {total}; hand word {h} pocket word {p} -> {"MATCH" if h + p == total or (p == 0 and h == total) else "OTHER"}')
png = os.path.join(OUT, 'gold_hand_merged.png'); s('render', path=png)
# cap: labelled pokes of hand = GOLD $ffd0 and pocket = GOLD 100 (not picked up: no such item exists), then $e7d0
s('poke', addr=A6 + 404, width=4, value=0x0019ffd0); s('poke', addr=pocket, width=4, value=0x00190064)
s.call_resume(0xe7d0, a0=pocket); h, p = state('cap test: hand 65488 + pocket 100')
print(f'     predicted hand 65500 ($ffdc), pocket 65588 - 65500 = 88: {"MATCH" if (h, p) == (65500, 88) else "OTHER"}')
s.close()
