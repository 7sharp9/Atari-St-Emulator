"""gate_pick.py <hits> <dump>: the attack pick $3dbb2-$3dbc0. A hit log from dm.lua with DM_ADDRS=3dbbc,3dbc0 (D0 at $3dbbc is the table index, D1 the roll rnd&$1f; D0 at $3dbc0 the byte read) and the dump of the same run:
checks index == 32*148(A6) + roll and picked == ROM byte at $3dbda + index, and the script that follows (153(A6) in the dump one frame later) == picked."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
root = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..'))
rom = open(os.path.join(root, 'scratchpad/finalfight/ff_main.bin'), 'rb').read()
D = Dump(sys.argv[2]); fr = list(D.frames()); fidx = {int(f): i for i, f in enumerate(fr)}
pend = None; ok_idx = ok_byte = ok_script = n = 0
for l in open(sys.argv[1]):
    p = l.split()
    if len(p) < 7 or p[1] not in ('3dbbc', '3dbc0'): continue
    f, a, d0, d1 = int(p[0]), p[1], int(p[2], 16), int(p[3], 16)
    if a == '3dbbc': pend = (f, d0, d1)
    elif pend:
        f0, idx, roll = pend; pick = d0; n += 1
        i = fidx.get(f0)
        ang = D.u8(i, BOSS + 148) if i is not None else None
        if ang is not None and idx == 32 * ang + roll: ok_idx += 1
        if rom[0x3dbda + idx] == pick: ok_byte += 1
        j = fidx.get(f0 + 2)
        if j is not None and D.u8(j, BOSS + 153) == pick: ok_script += 1
        pend = None
print('picks %d: index = 32*148 + roll %d, picked byte = ROM $3dbda[index] %d, 153(A6) two frames later = pick %d' % (n, ok_idx, ok_byte, ok_script))
