"""x6_hazard.py: follow a class-$80 mover (hazard) to its impact: L0 snapshot s86/a7/snaps/inj_room13.snap holds object 900 (template class $80, a clone of the fire/rock template).
Prints, per main-loop pass, the object's position, mover state/counters and the hero's health 1174(A5) until the object disappears; the health change is compared with the object's damage byte (inst+1 of its record)
and the code at $fa9c (health -= inst[1], after the shield test 2436/2437(A5)).  usage: x6_hazard.py [snapshot] [id]"""
import sys
from lab import *
snap = sys.argv[1] if len(sys.argv) > 1 else SN('ROOM13', 'scratchpad/cadaver/s86/a7/snaps/inj_room13.snap')
oid = int(sys.argv[2]) if len(sys.argv) > 2 else 900
r = start(snap); passes(r, 1)
S = sprites(r)
print('live objects', sorted(S), ' hero health %d' % r.w(A5 + 1174))
o = S[oid]; rec = o['rec']; h = r.mem(rec, 16)
print('obj %d: class %02x template+12 %02x  rec+3 %02x +15 %02x  inst %s  mover %s' % (oid, o['tm'][22], o['tm'][12], h[3], h[15], r.mem(rec + h[12], h[13] - h[12]).hex(' '), r.mem(rec + h[13], h[14] - h[13]).hex(' ')))
last = None; hp0 = r.w(A5 + 1174)
for k in range(300):
    rec = rec_of(r, oid)
    if rec is None or oid not in sprites(r):
        print('pass %d: object %d is gone; hero health %d (was %d); shield 2436(A5)=%02x 2437=%02x' % (k, oid, r.w(A5 + 1174), hp0, r.mem(A5 + 2436, 1)[0], r.mem(A5 + 2437, 1)[0])); break
    h = r.mem(rec, 16); m = r.mem(rec + h[13], 14)
    st = (tuple(r.mem(rec, 3)), m[0], tuple(m[3:6]), r.w(A5 + 1174))
    if st != last and (k < 4 or k % 10 == 0): print('pass %3d pos %s mover state %d counters %s health %d' % ((k,) + st))
    last = st; passes(r, 1)
r.close()
