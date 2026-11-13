"""The wall panel W of a lock, driven by mouse clicks in the emulator's D0 = 13 base (base13.snap).

panel13.py [lock] [bits]      default lock 4 (W (5,8), D (7,9), code $8520), bits = the code's set bits

Labelled pokes: the party's x, y, facing (fed 26/28/30(A6)) to stand on the cell W faces, facing it; nothing else.
One click on the closed cover first ($ddd2 sets bit 2 of W's tile). Then, per switch: pin the pointer, move to the switch, click, and read the lock record at 8628(A6) + 10 * lock
(state word +4, flag byte +8) and the tile of the door cell D. The switch positions come from the click handler
$12b4c: key kind 3 is a 5 x 5 grid of 5-pixel cells from (90,98), bit = table $12c12[row * 5 + col] - 1.
Prints the tile of D after every click; saves and renders the view before the first click and after the last under
scratchpad/captive/phoopel/.  Arms:
  code      the code's bits, in ascending order: D changes only on the last click
  control   the same clicks with the last bit left out, plus one wrong bit: D never changes
  walk      after `code`, pokes the party to (6,9) facing E (labelled) and presses forward twice
"""
import os, sys
_M = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))  # M68000/
sys.path.insert(0, _M + '/reversing/captive/py/ai')
from cap import R, StServer, A6, W  # noqa: E402

OUTD = os.path.join(W, 'phoopel')
SNAP = os.path.join(OUTD, 'base13.snap')
LOCKS, TILES, TABLE = A6 + 8628, A6 + 9242, 0x12c12
lock = int(sys.argv[1]) if len(sys.argv) > 1 else 4

s = StServer(R)
s('load', snapshot=SNAP)
w = lambda a: int.from_bytes(s.read(a, 2), 'big')
rec = lambda: s.read(LOCKS + 10 * lock, 10)
tile = lambda x, y: s.read(TILES + y * 64 + x, 1)[0]
r = rec()
wx, wy, code, dx_, dy_, kinds = r[0], r[1], int.from_bytes(r[2:4], 'big'), r[6], r[7], r[8]
table = s.read(TABLE, 25)
print(f'lock {lock}: W ({wx},{wy}) code ${code:04x} state ${int.from_bytes(r[4:6], "big"):04x} D ({dx_},{dy_}) '
      f'byte8 ${kinds:02x} (key kind {kinds & 3}, door kind {(kinds >> 2) & 3}) byte9 ${r[9]:02x}')
print('switch table $12c12:', ' '.join(f'{b:02x}' for b in table))
pos = {b - 1: (90 + 5 * (i % 5) + 2, 98 + 5 * (i // 5) + 2) for i, b in enumerate(table) if b}
print('bit -> click point:', {k: pos[k] for k in sorted(pos)})
bits = [int(b) for b in sys.argv[2].split(',')] if len(sys.argv) > 2 else [b for b in range(16) if code >> b & 1]
# the panel faces one way: it is drawn ($aab2-$aac0) and its cover opens ($dd96) only when (tile - facing) & 3 = 0
# (0 N, 1 W, 2 S, 3 E), so the party stands on the cell the panel faces
face = tile(wx, wy) & 3
px, py = wx - ((0, -1, 0, 1)[face]), wy - ((-1, 0, 1, 0)[face])
print(f'labelled pokes: party ({px},{py}) facing {face}; tile of W ${tile(wx, wy):02x}, of D ${tile(dx_, dy_):02x}')
s('poke', addr=A6 + 26, width=2, value=px)
s('poke', addr=A6 + 28, width=2, value=py)
s('poke', addr=A6 + 30, width=2, value=face)
s('step', n=180000)
base = s('fork')['id']


def click(x, y):
    for _ in range(3):
        s('mouse', action='move', dx=-127, dy=-127); s('step', n=30000)
    while x or y:
        mx, my = min(x, 120), min(y, 120)
        s('mouse', action='move', dx=mx, dy=my); s('step', n=30000); x -= mx; y -= my
    s('mouse', action='down', button='l'); s('step', n=60000)
    at = (w(A6 + 15152), w(A6 + 15154))   # the pointer as the game latched it for this click
    s('mouse', action='up', button='l'); s('step', n=300000)
    return at


def arm(name, seq):
    s('restore', id=base)
    s('save', path=os.path.join(OUTD, f'panel_{name}_before.snap'))
    s('render', path=os.path.join(OUTD, f'panel_{name}_before.png'))
    opened = []
    at = click(100, 110)
    print(f'  {name}: click the cover at {at}: tile W ${tile(wx, wy):02x}')
    s('render', path=os.path.join(OUTD, f'panel_{name}_open.png'))
    for b in seq:
        at = click(*pos[b])
        r = rec()
        t = tile(dx_, dy_)
        opened.append(t)
        print(f'  {name}: click bit {b:2d} at {at}: state ${int.from_bytes(r[4:6], "big"):04x} byte8 ${r[8]:02x} '
              f'byte9 ${r[9]:02x} tile D ${t:02x}')
    s('save', path=os.path.join(OUTD, f'panel_{name}_after.snap'))
    s('render', path=os.path.join(OUTD, f'panel_{name}_after.png'))
    return opened


print('arm code:', bits)
arm('code', bits)
opened = s('fork')['id']
wrong = next(b for b in range(16) if b not in bits)
print('arm control:', bits[:-1] + [wrong])
arm('control', bits[:-1] + [wrong])
print('arm walk (labelled pokes: party (%d,%d) facing 3, from the end of arm code)' % (dx_ - 1, dy_))
s('restore', id=opened)
s('poke', addr=A6 + 26, width=2, value=dx_ - 1)
s('poke', addr=A6 + 28, width=2, value=dy_)
s('poke', addr=A6 + 30, width=2, value=3)
s('step', n=180000)
for i in range(2):
    s('kbd', bytes=[0x68]); s('step', n=60000); s('kbd', bytes=[0xe8]); s('step', n=300000)
    print(f'  forward {i + 1}: party ({w(A6 + 26)},{w(A6 + 28)}) facing {w(A6 + 30)}')
s('save', path=os.path.join(OUTD, 'panel_walk_after.snap'))
s('render', path=os.path.join(OUTD, 'panel_walk_after.png'))
s.close()
