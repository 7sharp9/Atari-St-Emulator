import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ssh import *
r = R(os.path.join(AGENT, 'snap', 'pre_winner.snap'))
def words(off, n):
    b = r.mem(sscfg.A4 + off, 2 * n)
    return [int.from_bytes(b[i:i+2], 'big') for i in range(0, len(b), 2)]
for a in range(4):
    dur = words(-9144 + 26 * a, 13)
    img = words(-9040 + 26 * a, 13)
    s = lambda w: [(x - 65536 if x >= 0x8000 else x) for x in w]
    print('anim', a, 'durations', s(dur))
    print('       images   ', s(img))
r.close()
