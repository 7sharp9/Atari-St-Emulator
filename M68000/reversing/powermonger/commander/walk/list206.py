"""list206.py - recompute classify_stuck.py's class-b pairs and dump each one's record + tick-model verdict as JSON.
Usage (from M68000/): uv run python scratchpad/cmd2/agents/walker/list206.py out.json"""
import json, sys
from pathlib import Path
here = Path(__file__).resolve()
root = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(root / 'reversing/powermonger/commander'))
import classify_stuck as cs, astar, glob, re

out = []
for name in cs.SERIES:
    pre = str(root / 'scratchpad/pm148/arms/long' / name)
    snaps = sorted(glob.glob(pre + '_c*.snap'), key=lambda s: int(re.search(r'_c(\d+)\.snap$', s).group(1)))
    prev = None
    for s in snaps:
        r = astar.ram_from_snap(s)
        cur = cs.men(r)
        mp = None
        if prev is not None:
            for i, v in cur.items():
                p = prev.get(i)
                if not (p and (p['tx'], p['ty']) == (v['tx'], v['ty'])):
                    continue
                d0 = max(abs(p['tx'] - p['x']), abs(p['ty'] - p['y']))
                d1 = max(abs(v['tx'] - v['x']), abs(v['ty'] - v['y']))
                if d1 < d0 - 256:
                    continue
                if mp is None:
                    mp = astar.Map(r)
                k, info = cs.classify(mp, v)
                if k not in ('b', 'c'):
                    continue
                arr, tick, pos, modes = mp.simulate_walk((v['x'], v['y']), (v['tx'], v['ty']), v['speed'], 3000,
                                                         chase=v['prev'] == 0x2e)
                o = 0x51b66 + 50 * i
                out.append(dict(snap=s, obj=i, cls=k, arrives=arr, tick=tick, modes=sorted(modes),
                                rec=r[o:o + 50].hex(), **{kk: vv for kk, vv in v.items()}))
        prev = cur
json.dump(out, open(sys.argv[1], 'w'), indent=0)
print(len(out), sum(1 for d in out if d['cls'] == 'b' and d['arrives']), sum(1 for d in out if d['cls'] == 'c' and d['arrives']))
