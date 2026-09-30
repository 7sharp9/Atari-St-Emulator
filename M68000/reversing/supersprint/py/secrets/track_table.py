import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
r = R(sscfg.SNAP_ATTRACT)
def words(off, n):
    b = r.mem(sscfg.A4 + off, 2 * n)
    return [int.from_bytes(b[i:i+2], 'big') for i in range(0, len(b), 2)]
w = words(-1262, 40)
for t in range(10): print('track', t, w[t*4:t*4+4])
print('words after', words(-1262+80, 8))
r.close()
