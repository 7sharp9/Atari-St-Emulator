"""x4_gravity_bits.py: PROVES what rec+15 bits 2, 3, 4 do to the fall pointer 28(sprite) chosen by $00f3aa: bit 3 or bit 2 -> no gravity (0), bit 4 -> start at the terminal-velocity entry $5d8b, none -> start of the fall table $5d7f;
templates with +13 == 0 never fall.  callcap of $00f3aa (A0 = the object's sprite entry) for every combination of bits 2,3,4 on objects whose template +13 is non-zero / zero.
usage: x4_gravity_bits.py"""
import sys
from lab import *
r = start(SN('CAVERN', 'scratchpad/cadaver/gameplay_empire.snap')); passes(r, 2)
S = sprites(r)
tab = r.mem(0x5d7f, 0x20); print('fall table at $5d7f:', tab.hex(' '))
ok = n = 0
for oid in (412, 168, 60, 5, 413, 257):
    if oid not in S: continue
    o = S[oid]; rec = o['rec']; ent = o['ent']; t13 = o['tm'][13]; f15 = r.mem(rec + 15, 1)[0]
    row = []
    for bits in (0x00, 0x04, 0x08, 0x10, 0x14, 0x0c, 0x18):
        wb(r, rec + 15, (f15 & ~0x1c) | bits)
        res = callcap(r, 0xf3aa, 'A0=%x' % ent)
        d = res['delta']
        p = int(''.join('%02x' % d.get(ent + 28 + i, (0, r.mem(ent + 28 + i, 1)[0]))[1] for i in range(4)), 16)
        exp = 0 if (t13 == 0 or bits & 8 or (not bits & 0x10 and bits & 4)) else (0x5d8b if bits & 0x10 else 0x5d7f)
        row.append('%02x:%s%s' % (bits, hex(p), '' if p == exp else '!')); n += 1; ok += (p == exp)
    wb(r, rec + 15, f15)
    print('obj %3d template+13=%02x: %s' % (oid, t13, '  '.join(row)))
o = S[412]; ta = int.from_bytes(o['e'][6:10], 'big'); t13 = r.mem(ta + 13, 1)[0]; wb(r, ta + 13, 0)
res = callcap(r, 0xf3aa, 'A0=%x' % o['ent']); d = res['delta']
p = int(''.join('%02x' % d.get(o['ent'] + 28 + i, (0, r.mem(o['ent'] + 28 + i, 1)[0]))[1] for i in range(4)), 16)
wb(r, ta + 13, t13); n += 1; ok += (p == 0)
print('template+13 poked to 0 (obj 412, no +15 bits): fall pointer %s (expected 0)' % hex(p))
print('matches of the predicted rule (t13==0 or bit3 -> 0; bit4 -> $5d8b; bit2 -> 0; else $5d7f): %d of %d' % (ok, n))
r.close()
