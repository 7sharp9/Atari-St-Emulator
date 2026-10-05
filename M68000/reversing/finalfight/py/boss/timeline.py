"""timeline.py <dump>: DAMND (+2..+5) change list with hp, position, 190/191, 297/299, 278 and 1078 (camera lock), script pointer and pause flag, player 1 state and score, TIME."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from dd import *
D = Dump(sys.argv[1]); fr = D.frames()
A5 = 0xff8000
def g(i):
    return dict(f=int(fr[i]), s=(D.u8(i,BOSS+2), D.u8(i,BOSS+3), D.u8(i,BOSS+4), D.u8(i,BOSS+5)), hp=D.s16(i,BOSS+24), x=D.u16(i,BOSS+6), y=D.u16(i,BOSS+10),
        sa=(D.u8(i,A5+190), D.u8(i,A5+191)), n297=D.u8(i,A5+297), n299=D.u8(i,A5+299), n278=D.u16(i,A5+278), cam=D.u16(i,A5+1042), l1078=D.u16(i,A5+1078),
        scr=D.u32(i,0xffb1ee), pz=D.u8(i,0xffb1e8+22), exs=D.u8(i,0xffb1e8+2), pst=(D.u8(i,P1+2),D.u8(i,P1+3)), score=D.u32(i,P1+132), time=D.u8(i,A5+175), b0=D.u8(i,BOSS))
prev = None
for i in range(D.n):
    r = g(i)
    key = (r['s'], r['b0'], r['n297'], r['n299'], r['sa'], r['pz'], r['scr'], r['pst'], r['l1078'], r['n278'])
    if key != prev:
        print('%d st=%02x%02x%02x%02x b0=%02x hp=%d x=%04x y=%04x sa=%02x%02x 297=%02x 299=%02x 278=%04x cam=%04x 1078=%04x scr=%06x pz=%d exs=%02x pst=%02x%02x score=%08x time=%02x' % (
            r['f'], *r['s'], r['b0'], r['hp'], r['x'], r['y'], *r['sa'], r['n297'], r['n299'], r['n278'], r['cam'], r['l1078'], r['scr'], r['pz'], r['exs'], *r['pst'], r['score'], r['time']))
        prev = key
