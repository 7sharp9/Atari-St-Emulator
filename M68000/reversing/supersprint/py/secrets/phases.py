import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from probe import *
ADDRS = [0x1399e, 0x139ac, 0xcaa8, 0xd4c4, 0xdf18, 0x1b7e2, 0x1bc92, 0x16cb4, 0x16b98, 0x13a44, 0x1b458, 0x1b7e2]
r = R(sscfg.SNAP_ATTRACT)
for k in range(30):
    a = Acc(r, ADDRS)
    a.run(1000000)
    print('%5.1fM' % (k * 1.0), {hex(x): v for x, v in a.tot.items() if v})
r.close()
