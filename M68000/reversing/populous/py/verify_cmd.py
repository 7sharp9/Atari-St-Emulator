"""verify_cmd.py - compare emulator raise/lower commands (cmd_*.snap, made by writing a command into the
player-0 command record $21e0c and running to $1eedc) with popgen.Gen.raise_pt/lower_pt."""
import sys; sys.setrecursionlimit(100000)
import os
from popcfg import WORK
TW = os.path.join(WORK, 'agents', 'terrain')
from popmem import *; from popgen import Gen
base = ram(os.path.join(WORK,'game_start.snap'))
H0 = [sw(base, 0x34be4+2*i) for i in range(65*65)]
for name, fn, x, y in (('raise', 'raise_pt', 11, 16), ('lower', 'lower_pt', 11, 16), ('raise2', 'raise_pt', 30, 10)):
    m = ram(os.path.join(TW, 'cmd_%s.snap' % name))
    H1 = [sw(m, 0x34be4+2*i) for i in range(65*65)]
    g = Gen(0); g.h = list(H0); getattr(g, fn)(x, y)
    ch = [(i % 65, i//65, H0[i], H1[i]) for i in range(65*65) if H0[i] != H1[i]]
    print(name, (x, y), 'emu changed', len(ch), 'python==emu', g.h == H1, 'steps($37f8a) emu', w(m, 0x37f8a), 'py', g.raises,
          'mana', l(base, 0x3b232), '->', l(m, 0x3b232), 'expected', l(base, 0x3b232) - (4*g.raises+10),
          'bbox emu', [sw(m, a) for a in (0x36ce8, 0x3b006, 0x3d522, 0x37eb8)])
