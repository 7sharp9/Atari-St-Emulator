"""bit6_corr.py: correlation of rec+3 bit 6 with the object's event-9 blocks: a block with gate word 0 answers contact with the hero ($006d90/$00934a queue event 9 [record][0] only for records with +3 bit 6);
a block with another id answers an object-object contact (queued by the collision routine $008a14/$008a3a for any pair).  usage: bit6_corr.py SNAP..."""
import sys, collections
from st import St
for snap in sys.argv[1:]:
    s = St(snap); c = collections.Counter(); ex = collections.defaultdict(list)
    for i in range(s.count(6)):
        a = s.obj(i)
        if a is None: continue
        sz = s.size(6, i); r = s.mem(a, sz)
        if r[15] & 0x80: continue
        p = 0x10
        for _ in range(r[11]):
            ln = r[p]; ev = r[p + 1] & 0x7f
            if ev == 9:
                g = int.from_bytes(r[p + 2:p + 4], 'big'); kind = 'hero(0)' if g == 0 else 'other id'
                c[(kind, bool(r[3] & 0x40))] += 1; ex[(kind, bool(r[3] & 0x40))].append(i)
            p += ln
    print(snap, {'%s bit6=%s' % k: v for k, v in sorted(c.items())})
    for k, v in sorted(ex.items()): print('   ', k, sorted(set(v))[:12])
    # and the converse: objects with bit 6 and no event-9 block
    none = []
    for i in range(s.count(6)):
        a = s.obj(i)
        if a is None: continue
        r = s.mem(a, s.size(6, i))
        if r[15] & 0x80 or not r[3] & 0x40: continue
        p = 0x10; has = False
        for _ in range(r[11]):
            if r[p + 1] & 0x7f == 9: has = True
            p += r[p]
        if not has: none.append(i)
    print('    objects with +3 bit 6 and no event-9 block:', len(none), none[:12])
