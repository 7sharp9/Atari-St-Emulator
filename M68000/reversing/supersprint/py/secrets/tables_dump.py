import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
r = R(sscfg.SNAP_ATTRACT)
def words(off, n):
    b = r.mem(sscfg.A4 + off, 2 * n)
    return [int.from_bytes(b[i:i+2], 'big') for i in range(0, len(b), 2)]
for off, n in ((-8542, 10), (-8526, 10), (-8682, 8), (-8768, 8), (-4814, 4), (-3914, 4), (-8066, 8), (-8342,8),(-3906,4),(-4822,4)):
    print(off, words(off, n))
r.close()
