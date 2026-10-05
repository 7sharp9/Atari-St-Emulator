"""stagger.py <probe.txt>...: run lengths of state 1 (stagger) per type: ~15 frames = weak stagger (pushback 0.5 px/frame), >= 60 = knockback roll (strong hit or 1 in 4 of kind-1/2 hits),
with the hit flags (+6) seen on the frame before the run."""
import sys, collections
res = collections.defaultdict(collections.Counter)
for path in sys.argv[1:]:
    cur = {}; prev = {}
    for line in open(path):
        p = line.split()
        if p[0] != "A": continue
        f, slot, b = int(p[1]), int(p[2]), bytes.fromhex(p[3])
        c = cur.get(slot); pv = prev.get(slot)
        if b[3] == 1 and (c is None or c[0] + c[1] != f):
            cur[slot] = [f, 1, b[2], pv[6] if pv and pv[0] == f - 1 else None]
        elif b[3] == 1 and c: c[1] += 1
        elif c and c[0] + c[1] == f:
            res[(c[2], c[3] & 0x8b if c[3] is not None else None)][("weak" if c[1] < 40 else "roll")] += 1; cur[slot] = None
        prev[slot] = (f, b[3], 0, 0, 0, 0, b[6])
for k in sorted(res, key=lambda k: (k[0], k[1] or 0)):
    print(f"type {k[0]:02x} hit flags(+6 & $8b) {k[1] if k[1] is None else hex(k[1])}: {dict(res[k])}")
