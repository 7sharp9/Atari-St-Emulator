"""exe.py <dump> [lo hi]: stage-script executor record $ffb1e8 (+2 state, +22 pause flag, +6 script pointer long at $ffb1ee, +24 continuation) and DAMND's (+2,+3,+4) per change, with 190/191, 297, 299."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
D = Dump(sys.argv[1]); fr = D.frames()
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0; hi = int(sys.argv[3]) if len(sys.argv) > 3 else 10**9
prev = None
for i in range(D.n):
    f = int(fr[i])
    if f < lo or f > hi: continue
    k = (D.u8(i, 0xffb1e8 + 2), D.u8(i, 0xffb1e8 + 22), D.u32(i, 0xffb1ee), D.u8(i, 0xff8000 + 190), D.u8(i, 0xff8000 + 191), D.u8(i, BOSS), D.u8(i, BOSS + 2), D.u8(i, BOSS + 3), D.u8(i, 0xff8000 + 297), D.u8(i, 0xff8000 + 299))
    if k != prev:
        print(f, 'exec +2=%02x pause=%d scr=%06x | sa=%02x%02x | boss b0=%02x st=%02x%02x | 297=%02x 299=%02x | cont=%06x hp=%d cam=%04x' % (*k, D.u32(i, 0xffb1e8 + 24) & 0xffffff, D.s16(i, BOSS + 24), D.u16(i, 0xff8000 + 1042)))
        prev = k
