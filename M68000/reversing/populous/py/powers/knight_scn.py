"""knight_scn.py - a knight that can reach the enemy: cast through the UI, then let it play.

GENESIS puts the human on an island (x 0..20, y 2..21) and the knight cast from drive/A walks
into the southern shore and starves (ktrack.py: str 50 -> 0 by frame ~720, never leaving y 21).
State preparation (documented pokes, then everything is the real game):
  * a land corridor on the knight's own heading: corners along (10+t, 21+t) t=0..16 then
    (26, 37+t) t=0..19, 4 corners wide, raised to max(h, 1), cells re-derived with the $c0ee
    model (powers_ref.derive_cells) only where a corner changed;
  * at the entry of $12ba0 the leader's str (entity 2, a settlement of 51) is set to STR, so the
    knight survives the walk.
Then: popdrive click on the knight icon -> $12ba0 (entry/exit snaps, model compare as cast.py),
and the run continues. Output: snaps/kbridge_{entry,exit,after}.snap.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pwlib import *
import powers_ref as P
import cast as C
from popdrive import Game

STR = int(os.environ.get('KSTR', '600'))


def bridge(m0):
    m1 = bytearray(m0)
    pts = [(10 + t, 21 + t) for t in range(17)] + [(26, 37 + t) for t in range(20)]
    cells = set()
    for x, y in pts:
        for cy in range(y - 1, y + 3):
            for cx in range(x - 1, x + 3):
                a = P.HGT + 2 * (cx + 65 * cy)
                if P.rw(m1, a) < 1:
                    P.ww(m1, a, 1)
                    for dy in (-1, 0):
                        for dx in (-1, 0):
                            if 0 <= cx + dx < 64 and 0 <= cy + dy < 64:
                                cells.add((cx + dx, cy + dy))
    for cx, cy in sorted(cells):
        P.derive_cells(m1, cx, cy, cx, cy)
    return m1


def set_str(i, v):
    def f(r):
        a = P.ent(i) + 4
        lo = r.mem(a + 2, 2)
        r.cmd('w %x %08x' % (a, ((v & 0xffff) << 16) | int.from_bytes(lo, 'big')))
    return f


if __name__ == '__main__':
    A = os.path.join(WORK, 'drive', 'A.snap')
    m0 = ram(A)
    m1 = bridge(m0)
    pk = C.poke_lines(m0, m1)
    g = Game(bytes(m1))
    L, _ = C.icon_click(g, 'knight')
    C.cast('kbridge', 'drive/A.snap', 'knight', L, [C.MANA] + pk, [set_str(2, STR)])
