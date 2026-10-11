"""pend_pigeons.py <snap>...: per side 1..4, each group's owner/men/pending/state/lead (structure-of-arrays, word n of group k at
slot + n + 2k, slot = $51538 + side*$13c, from $6564), and every live order pigeon ($4c12c..$4c5f2, 26 bytes) with its rider."""
import sys
from pathlib import Path
ROOT = next(p for p in Path(__file__).resolve().parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap
OBJ = 0x51b66
def w(r, a): return (r[a] << 8) | r[a + 1]
def s16(v): return v - 0x10000 if v & 0x8000 else v
sides = [int(x) for x in (sys.argv[2].split(',') if len(sys.argv) > 2 else '1,2,3,4'.split(','))]
r = ram_from_snap(sys.argv[1])
print('clock $2df72 =', w(r, 0x2df72), ' local side $57ffe =', w(r, 0x57ffe))
for sd in sides:
    slot = 0x51538 + sd * 0x13c
    for k in range(6):
        A1 = slot + 2 * k
        own = s16(w(r, A1 + 28))
        if own <= 0: continue
        lead = (OBJ + s16(w(r, A1 + 64))) & 0xfffff
        print(' side %d grp %d (D7=%d) owner %d men %d pending %d state %d camp %d lead %x (own %d hp %d mode %02x w42 %04x)' % (
            sd, k, 2 * k, own, w(r, A1 + 52), s16(w(r, A1 + 4)), w(r, A1 + 76), s16(w(r, A1 + 256)), lead, s16(r[lead + 5] - 0 if r[lead+5] < 128 else r[lead+5]-256), r[lead + 45], r[lead + 31], w(r, lead + 42)))
for i in range(48):
    p = 0x4c112 + 26 * i
    if r[p + 6] == 0: continue
    rid = (OBJ + s16(w(r, p + 20))) & 0xfffff
    o = r[p + 5] - 256 if r[p + 5] > 127 else r[p + 5]
    if sd and abs(o) not in sides and i: pass
    print(' pigeon %d @%x own %d cat %02x pos (%d,%d) t18 %d b15 %d rider %x (own %d mode %02x w42 %04x pos (%d,%d)) order %02x %04x' % (
        i, p, o, r[p + 6], w(r, p + 8), w(r, p + 10), s16(w(r, p + 18)), r[p + 15], rid, r[rid + 5] - 256 if r[rid + 5] > 127 else r[rid + 5], r[rid + 31], w(r, rid + 42), w(r, rid + 8), w(r, rid + 10), r[p + 23], w(r, p + 24)))
