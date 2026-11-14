"""control_water_blind.py - broken-model control for the movement-model gate in report.py.
The gate: the game-rule tick model (astar.Map.simulate_walk) says "stuck" for the census's stuck pairs (a, a-twater, b).
Broken model: the terrain probe never sees water (Map.sample always 1). The gate must then fail.
Usage (from M68000/): uv run python reversing/powermonger/commander/bug2/control_water_blind.py   (needs pairs.pkl from extract_pairs.py)"""
import pickle
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import follow
from follow import astar, ROOT, DATA

P = pickle.load(open(DATA / 'pairs.pkl', 'rb'))['pairs']
maps, tot, stuck = {}, 0, 0
for p in P:
    if p['cls'] not in ('a', 'a-twater', 'b'):
        continue
    if p['plane'] not in maps:
        mp = astar.Map(str(ROOT / 'scratchpad/pm148/arms/long' / (p['snap'] + '.snap')))
        mp.sample = lambda x, y: 1                      # the one change: no water anywhere
        maps[p['plane']] = mp
    arr, _t, _pos, _m = maps[p['plane']].simulate_walk((p['x'], p['y']), (p['tx'], p['ty']), p['speed'], 3000, chase=p['prev'] == 0x2e)
    tot += 1
    stuck += (not arr)
print('water-blind model says stuck for %d/%d stuck pairs (the real model: 3751/3957)' % (stuck, tot))
