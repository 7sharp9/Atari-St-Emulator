"""Natural (unpoked, policy auto) capture for the bomber gates: as behaviours/cap_nat.py, but through bcap.py, which stamps the
bomber's own code (entry, exit, heading draw, bomb spawn, 21 plants, bomb handler, burst) with the RNG state and registers.

    uv run python cap_b.py <snapshot> <ticks> <out.json>
"""
import json, os, sys, time
here = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, here)
import bcap as C
C.EV.update({0x22164: 'p2_hit1', 0x20206: 'provoke', 0x201b4: 'provoke_entry'})
snap, N, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
hm = {}
def hook(g, k, row):
    w = row['wave']
    if w not in hm:
        hm[w] = g.s('read', addr=0x42a58, len=0x10000)
    row['hw'] = w
t0 = time.time()
cap = C.capture('auto', N, snap=snap, hook=hook)
for k in ('map1', 'hmap'):   # map0 kept: the object map at the first arrival, to replay the plants' writes
    cap.pop(k)
cap['hmaps'] = hm
json.dump(cap, open(out, 'w'))
print(len(cap['rows']), 'ticks', round(time.time() - t0), 's, waves', sorted(hm))
