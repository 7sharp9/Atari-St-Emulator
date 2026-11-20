"""Natural (unpoked, policy auto) capture through a wave change, for the attractor gates.

    uv run python cap_att.py <snapshot> <ticks> <out.json> [cap_steps]

cap_nat.py's capture with a larger per-tick step cap: the wave change ('wave start', no $255d4 arrival for tens of millions
of steps) ended every capture of pursuer/caps at 'max_steps' with the 8M cap. Rows as shot_capture.capture writes them
(ship pos/vel/att/fuel, flags, pool, events), plus 'hw' (wave) and the height map of each wave in 'hmaps'."""
import json, os, sys, time
d = os.path.dirname(os.path.abspath(__file__)); R_ = d
while not os.path.exists(os.path.join(R_, 'tools', 'rdis.py')):
    R_ = os.path.dirname(R_)
sys.path.insert(0, os.path.join(R_, 'reversing/virus/py/mpc'))
import shot_capture as C
C.EV.update({0x22164: 'p2_hit1', 0x20206: 'provoke', 0x201b4: 'provoke_entry'})
snap, N, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
cap = int(sys.argv[4]) if len(sys.argv) > 4 else 80000000
hm = {}
def hook(g, k, row):
    w = row['wave']
    if w not in hm:
        hm[w] = g.s('read', addr=0x42a58, len=0x10000)
    row['hw'] = w
t0 = time.time()
c = C.capture('auto', N, snap=snap, hook=hook, cap=cap)
for k in ('map0', 'map1', 'hmap'):
    c.pop(k)
c['hmaps'] = hm
json.dump(c, open(out, 'w'))
print(len(c['rows']), 'ticks', round(time.time() - t0), 's, waves', sorted(hm), 'last', c['rows'][-1].get('stopped'))
