"""model206.py - walker.simulate from each class-b/c pair's full record state (not a fresh $10 start).
Usage: model206.py bc_before.json out.json"""
import json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import walker
d = json.load(open(sys.argv[1]))
maps = {}
out = []
for x in d:
    if x['snap'] not in maps:
        maps = {x['snap']: walker.astar.Map(x['snap'])}
    mp = maps[x['snap']]
    st = walker.decode(bytes.fromhex(x['rec']))
    try:
        arr, t, s = walker.simulate(mp, st, 3000)
        x['full_arrives'], x['full_tick'] = arr, t
        x['full_end'] = s['mode']
    except walker.Unmodelled as e:
        x['full_arrives'], x['full_tick'], x['full_end'] = None, None, str(e)
    out.append(x)
json.dump(out, open(sys.argv[2], 'w'))
import collections
print(collections.Counter((x['cls'], x['arrives'], x['full_arrives']) for x in out))
