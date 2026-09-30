import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from difflib_ss import *
h = Harness(sscfg.SNAP_RACE)
drv = Driver(h, 1)
snaps = []
for i in range(9):
    drv.poke_input()
    h.run_to(0xdf18, 1)
    r = h.snap_ram()
    snaps.append(P.Mem(r.b))
    m = snaps[-1]
    print(i, 'X', [m.a(P.X, c) for c in range(4)], 'Q', [m.a(P.QX, c) for c in range(4)], 'spd', [m.a(P.SPD, c) for c in range(4)], '-8072', m.gu(-8072), '-8478', m.gu(-8478), 'joy', hex(m.rb(A4 - 4804)))
h.close()
