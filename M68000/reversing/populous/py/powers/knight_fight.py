"""knight_fight.py - a knight cast through the UI in the middle of a fight-mode battle.

usage: python knight_fight.py [STR]      (from M68000/; default STR 0 = no strength poke)

From walker/snaps/fight1.snap (frame 2665), with the side-0 mana poked to 200000 (cast.py's MANA),
popdrive clicks the knight icon -> $12ba0, compared on the full state as cast.py does. With STR > 0
the leader's str is set to STR at the entry of $12ba0 (as knight_scn.py does), so the knight lives
long enough to cross the battlefield. Output: snaps/knight_s<STR>_{entry,exit,after}.snap, then
    live.py snaps/knight_s<STR>_after.snap 2000 merge resolve fightstart join
follows it (mechanics.md 3.3, 3.5).
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pwlib import *
import powers_ref as P
import cast as C
from popdrive import Game

BASE = 'walker/snaps/fight1.snap'


def main():
    st = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    m = ram(os.path.join(WORK, BASE))
    ld = P.rw(m, P.SIDE) - 1

    def strpoke(r):
        a = P.ent(ld) + 4
        v = r.mem(a, 4)
        r.cmd('w %x %04x%02x%02x' % (a, st, v[2], v[3]))     # str word; the t6 word after it kept

    L, _ = C.icon_click(Game(bytes(m)), 'knight')
    C.cast('knight_s%d' % st, BASE, 'knight', L, [C.MANA], [strpoke] if st else [])
    print(os.path.join(C.SN, 'knight_s%d_after.snap' % st))


if __name__ == '__main__':
    main()
