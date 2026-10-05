"""thresh.py <dump>: DAMND's hp-threshold flags: changes of 165 (retreat stage), 164 (retreat pending), 169 (angry stage), 148 (angry flag), 168 (retreat latched), 163 (player mask) with the hp before and after."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
D = Dump(sys.argv[1]); fr = D.frames()
names = {163: 'players', 165: 'ret_stage', 164: 'ret_pending', 168: 'ret_latch', 169: 'angry_stage', 148: 'angry', 160: 'in_range', 149: 'attacking', 174: 'moved'}
prev = {}
for i in range(D.n):
    if not D.u8(i, BOSS): continue
    for o, n in names.items():
        v = D.u8(i, BOSS + o)
        if o in prev and prev[o] != v and o in (163, 165, 164, 168, 169, 148):
            print('%d %-12s %d -> %d  hp %d -> %d  state %02x%02x%02x%02x' % (int(fr[i]), n, prev[o], v, D.s16(i-1, BOSS+24), D.s16(i, BOSS+24), D.u8(i,BOSS+2), D.u8(i,BOSS+3), D.u8(i,BOSS+4), D.u8(i,BOSS+5)))
        prev[o] = v
