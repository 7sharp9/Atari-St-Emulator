import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
r = R(sscfg.SNAP_RACE)
a = Acc(r, [0xdf18, 0xc9de, 0xc9fa, 0x13b30, 0x138b2, 0x13a5e, 0x19164, 0x1399e, 0x139ac, 0x13982, 0xcaa8])
a.run(1500000)
a.press(['44'], 60000)
for k in range(8):
    a.tot = {x: 0 for x in a.tot}
    a.run(500000)
    print(k, {hex(x): v for x, v in a.tot.items() if v}, hex(a.regs['PC']))
r.close()
