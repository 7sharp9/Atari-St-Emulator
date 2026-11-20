"""Natural (unpoked, policy auto) capture of a Virus run for the pursuer/patrol gates.

    uv run python reversing/virus/py/behaviours/cap_nat.py <snapshot> <ticks> <out.json>

Wraps reversing/virus/py/mpc/shot_capture.capture (rows: ship, RNG, queue, tick44, actor pool, events per arrival) and, through the
capture hook, reads the height map $42a58 (64 KB) whenever the wave word $32a50 takes a value not seen yet, so the gate uses the map
of the wave the record was in (a wave start can change the landscape). Writes only <out.json>: {'snap','rows','hmaps':{wave: hex}}."""
import json, os, sys, time
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import vcommon
ROOT = vcommon.ROOT
sys.path.insert(0, os.path.join(ROOT, 'reversing/virus/py/mpc'))
import shot_capture as C
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
for k in ('map0', 'map1', 'hmap'):
    cap.pop(k)
cap['hmaps'] = hm
json.dump(cap, open(out, 'w'))
print(len(cap['rows']), 'ticks', round(time.time() - t0), 's, waves', sorted(hm))
