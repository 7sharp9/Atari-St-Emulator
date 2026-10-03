"""x13_event11_fall.py: the fall step $00f530 and its landing event.  Object 198 (the urn, L0 room 53, resting on z = 18, fall pointer 28(sprite) = 0) is armed the way $f3aa arms it (28(sprite) := $5d7f) and lifted by
+14 (rec z, sprite z at +4 and +5; the second run drops it to z = 1 instead); the mover patrol is stopped (+3 bit 4 cleared) so only the fall acts.  Each pass its z follows the fall table entries ($5d7f: ff ff fe fe fd ...); when z reaches 0 the code at
$00f69c pushes event 11 [record] (the urn's own block: 'THE URN SMASHES').  Prints z / pointer per pass and the ring entry at the push.   usage: x13_event11_fall.py"""
import sys
from lab import *
SNAP = SN('URN53', 'scratchpad/cadaver/s87/b3/work/r16/s13_b.snap')
def arm(r, dz=0x0e):
    rec = rec_of(r, 198); e = sprites(r)[198]['ent']
    wb(r, rec + 3, r.mem(rec + 3, 1)[0] & ~0x10)
    wb(r, rec + 2, r.mem(rec + 2, 1)[0] + dz); wb(r, e + 4, r.mem(e + 4, 1)[0] + dz); wb(r, e + 5, r.mem(e + 5, 1)[0] + dz); wl(r, e + 28, 0x5d7f)
    return rec, e
r = start(SNAP); passes(r, 2)
rec, e = arm(r); zs = []
for k in range(24):
    rc = rec_of(r, 198)
    if rc is None: zs.append('gone'); break
    zs.append('%02x/%x' % (r.mem(rc + 2, 1)[0], r.l(e + 28))); passes(r, 1)
print('z / fall pointer per pass:', ' '.join(zs))
r.close()
r = start(SNAP); passes(r, 2); rec, e = arm(r, -0x11)           # z = 1: the first table entry ($ff = -1) brings it to 0
o = r.cmd('u f69c 800000')
if any('gave up' in l for l in o): print('push site $f69c NOT reached within 800,000 steps with z = 1 (the pedestal blocks the drop): event 11 not reproduced live, only read from the code')
else:
    wp = r.l(A5 + 304); ent = bytes(r.mem(wp - 8, 8))
    print('push at $f69c: ring entry %s -> opcode %d, record $%x (urn record $%x), word %d' % (ent.hex(' '), int.from_bytes(ent[:2], 'big'), int.from_bytes(ent[2:6], 'big'), rec, int.from_bytes(ent[6:8], 'big')))
r.close()
