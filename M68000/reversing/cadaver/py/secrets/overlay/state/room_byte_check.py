"""room_byte_check.py: rec+10 is the room: for every room's type-5 object-id list (resource type 5, one list per room: words of type-6 ids), compare rec+10 of each listed id with the room index.  Also the
count rec+11 vs the number of first-list script blocks parsed from +$10 (they end exactly at rec[12]) and rec+8 (sprite-array offset: 0/garbage until instantiated).  usage: room_byte_check.py SNAP..."""
import sys
from st import St
for snap in sys.argv[1:]:
    s = St(snap); ok = n = 0; bad = []; seen = set()
    for room in range(s.count(5)):
        a = s.res(5, room)
        if a is None: continue
        sz = s.size(5, room)
        for k in range(0, sz, 2):
            oid = s.w(a + k)
            if oid == 0: continue                                # id 0 is the hero (room lists are zero padded)
            ra = s.obj(oid)
            if ra is None: continue
            n += 1; seen.add(oid)
            if s.b(ra + 10) == room: ok += 1
            else: bad.append((room, oid, s.b(ra + 10)))
    total = sum(1 for i in range(s.count(6)) if s.obj(i) is not None)
    print(snap, 'listed objects whose rec+10 equals the room of the list: %d of %d (exceptions %s); records with a room list entry: %d of %d' % (ok, n, bad[:6], len(seen), total))
