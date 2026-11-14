"""live_prep.py <snap> <obj> : bug2 path of one stuck man, string-pulled into waypoints each walkable by the game's leg rule."""
import sys, json
from pathlib import Path
here = Path(__file__).resolve()
sys.path.insert(0, str(here.parent))
import follow
from follow import DATA
from follow import astar, ROOT
snap, obj = sys.argv[1], int(sys.argv[2])
mp = astar.Map(ROOT / snap)
r = mp.ram
rec = 0x51b66 + 50 * obj
sw = lambda a: int.from_bytes(r[a:a + 2], 'big', signed=True)
s, t, speed = (sw(rec + 8), sw(rec + 10)), (sw(rec + 20), sw(rec + 22)), r[rec + 16]
tr = follow.Terrain(mp)
best = None
for hand in (1, -1):
    res, pts = follow.trace(tr, s, t, speed, algo='bug2', hand=hand, a0=16, turn=16)
    print('hand', hand, res['ok'], res['why'], res['ticks'], round(res['length']))
    if res['ok'] and (best is None or res['length'] < best[0]):
        best = (res['length'], pts, hand)
pts = best[1]
wps, cur, i = [], s, 0
while True:
    if mp.walkable(cur, t, speed):
        wps.append(t); break
    j = None
    for k in range(len(pts) - 1, i, -1):
        if mp.walkable(cur, pts[k], speed):
            j = k; break
    assert j is not None
    wps.append(pts[j]); cur, i = pts[j], j
legs = [mp.simulate_walk(a, b, speed, 3000)[:2] for a, b in zip([s] + wps, wps)]
print('start', s, 'target', t, 'speed', speed, 'hand', best[2], 'waypoints', len(wps), wps)
print('model legs (arrives, ticks):', legs)
json.dump(dict(start=s, target=t, speed=speed, wps=wps, legs=legs), open(str(DATA / ('live_%s_obj%d.json' % (Path(snap).stem, obj))), 'w'))
