"""immune.py <probe.txt>: run lengths of the pause/immunity window (+0 bit 3 set) per enemy type and the state it starts in, to test the 16-frame window of $24022
(+17 bit 3 set by the end of the stagger $2356e -> +0 bit 3 for 16 frames, hits are ignored by $22c56/$22ce4 while it is set)."""
import sys, collections
runs = collections.defaultdict(collections.Counter)
cur = {}
last = {}
for line in open(sys.argv[1]):
    p = line.split()
    if p[0] != "A": continue
    f, slot, b = int(p[1]), int(p[2]), bytes.fromhex(p[3])
    on = bool(b[0] & 8)
    c = cur.get(slot)
    if on and not c: cur[slot] = [f, b[2], b[3], 1, b[16]]
    elif on and c and c[0] + c[3] == f: c[3] += 1
    elif c and (not on or c[0] + c[3] != f):
        runs[(c[1], c[4], c[2])][c[3]] += 1; cur[slot] = [f, b[2], b[3], 1, b[16]] if on else None
for k, v in sorted(runs.items()):
    print(f"type {k[0]:02x} var {k[1]:x}, window began in state {k[2]:x}: run lengths " + ", ".join(f"{n}x{c}" for n, c in sorted(v.items())))
