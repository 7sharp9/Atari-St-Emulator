"""x7_relock.py: does rec+15 bit 2 (lock) stop a mover?  Run the lever-562 chain (e4) twice, once as is and once re-locking object 670 (poke +15 bit 2) three passes after GOMOVE: its z keeps rising either way,
so the mover pass never reads the lock bit (lock only matters to collision, gravity and the action panel)."""
import sys
from lab import *
for relock in (False, True):
    r = start(SN('ROOM90', 'scratchpad/cadaver/s90/run1/end_room90.snap')); passes(r, 2)
    fire(r, 562, 5)
    zs = []
    for k in range(20):
        b = rec_of(r, 670)
        if relock and k == 3: wb(r, b + 15, r.mem(b + 15, 1)[0] | 4)
        zs.append((r.mem(b + 2, 1)[0], r.mem(b + 15, 1)[0])); passes(r, 1)
    print('re-locked at pass 3' if relock else 'as scripted      ', 'z / +15 every third pass:', ' '.join('%02x/%02x' % z for z in zs[::3]))
    r.close()
