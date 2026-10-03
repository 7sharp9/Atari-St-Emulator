"""x8_examine_bit5.py: PROVES rec+3 bit 5 (examine has a script) at the examine producer $00a3d0: callcap with A1 = record, A2 = template.
bit 5 set: queues [event 16][record] (1154(A5) + 1, ring entry $0010); bit 5 clear: no queue entry; the class test then picks the generic description ($a426) or the message $03 ('nothing special').
Objects: 168 (pickaxe, +3 bit 5 set, class 0), 412 (coin), 60 (class 2), 257 (boat).  usage: x8_examine_bit5.py"""
import sys
from lab import *
r = start(SN('CAVERN', 'scratchpad/cadaver/gameplay_empire.snap')); passes(r, 2)
S = sprites(r); wp = A5 + 304
for oid in (168, 412, 257, 60, 5):
    if oid not in S: continue
    o = S[oid]; rec = o['rec']; ta = int.from_bytes(o['e'][6:10], 'big'); f3 = r.mem(rec + 3, 1)[0]
    out = []
    for bit5 in (1, 0):
        wb(r, rec + 3, (f3 & ~0x20) | (0x20 if bit5 else 0))
        res = callcap(r, 0xa3d0, 'A1=%x A2=%x' % (rec, ta), steps=60000)
        d = res['delta']
        q = d.get(A5 + 1154 + 1, (None, None))[1]            # low byte of 1154(A5)
        ring = [(hex(a), '%02x' % v[1]) for a, v in sorted(d.items()) if r.l(A5 + 152) <= a < r.l(A5 + 152) + 1600]
        m2142 = d.get(A5 + 2143, (None, None))[1]
        out.append('bit5=%d: returned %s, 1154(A5) low byte %s, ring writes %s, 2142(A5) low byte %s' % (bit5, res['ret'], q, ring[:4], m2142))
    wb(r, rec + 3, f3)
    print('obj %3d class %02x +3=%02x | %s' % (oid, o['tm'][22], f3, ' | '.join(out)))
r.close()
