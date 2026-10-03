"""door_census.py: census of type-4 door descriptors (those named in a room record's door list, record +6, 7 words, $ffff = none) of a snapshot: id word (+2) category and +7 bits.
usage: door_census.py SNAP..."""
import sys, collections
from st import St
for snap in sys.argv[1:]:
    s = St(snap); doors = {}
    for room in range(s.count(3)):
        a = s.res(3, room)
        if a is None: continue
        for i in range(7):
            d = s.w(a + 6 + 2 * i)
            if d == 0xffff: continue
            doors.setdefault(d, set()).add(room)
    cat = collections.Counter(); b7 = collections.Counter(); both = collections.Counter(); sz = collections.Counter()
    for d, rooms in sorted(doors.items()):
        ra = s.res(4, d)
        if ra is None: continue
        r = s.mem(ra, 8); w = int.from_bytes(r[2:4], 'big')
        c = 'zero' if w == 0 else 'ffff' if w == 0xffff else 'item'
        cat[c] += 1; b7[r[7]] += 1; both[(c, r[7])] += 1; sz[s.size(4, d)] += 1
    print(snap, 'doors named by room lists: %d' % len(doors), dict(cat), '+7 values', {hex(k): v for k, v in b7.items()}, 'size', dict(sz))
    print('   (category, +7):', {(c, hex(b)): v for (c, b), v in sorted(both.items())})
