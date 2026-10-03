"""a3: ev1_effect.py -- what the event-1 block of object 51 (verb 32 'current obj state bit 0 = 1') changes: RAM diff between a run with [1][obj 51][132] injected and a control run without, both 60,000 steps from gameplay_empire.snap (level 0)."""
from probe import *
from consumer_bits import push
import numpy as np
def ram_after(entries):
    h = HH.H(ROOT + '/scratchpad/cadaver/gameplay_empire.snap')
    if entries: push(h, entries(h))
    h.r.cmd('s 60000')
    a = HH.snap_ram(h, 'ev1'); a51 = h.obj(51); h.close(); return a, a51
a, a51 = ram_after(lambda h: [(1, h.obj(51), 132)])
b, _ = ram_after(None)
d = np.nonzero(a != b)[0]
print('bytes differing between the injected run and the control: %d' % len(d))
rel = [(hex(int(i)), int(b[i]), int(a[i])) for i in d if not (0x18152 <= i < 0x18152 + 0x1400)]
print('outside the A5 area:', rel[:20])
print('inside the A5 area:', [('%+d' % (int(i) - 0x18152), int(b[i]), int(a[i])) for i in d if 0x18152 <= i < 0x18152 + 0x1400][:30])
print('object 51 record at %06x; bytes %s' % (a51, bytes(a[a51:a51 + 0x40]).hex()))
