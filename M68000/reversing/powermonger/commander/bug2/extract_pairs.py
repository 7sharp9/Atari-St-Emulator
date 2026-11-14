"""extract_pairs.py - dump the classify_stuck.py stuck pairs (same census loop) to pairs.pkl, plus the terrain planes
per series. Usage (from M68000/): uv run python reversing/powermonger/commander/bug2/extract_pairs.py [out.pkl]"""
import glob, pickle, re, sys, hashlib
from pathlib import Path
here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'reversing/powermonger/commander'))
import astar, classify_stuck as cs
sys.path.insert(0, str(here.parent))
from follow import DATA

out = sys.argv[1] if len(sys.argv) > 1 else str(DATA / 'pairs.pkl')
pairs, planes = [], {}
for ser in cs.SERIES:
    pre = str(ROOT / 'scratchpad/pm148/arms/long' / ser)
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
                    blob = bytes(r[astar.PLANE_A:astar.PLANE_A + 8192]) + bytes(r[astar.PLANE_B:astar.PLANE_B + 8192]) + bytes(r[astar.FLAGS:astar.FLAGS + 8192])
                    h = hashlib.md5(blob).hexdigest()
                    planes.setdefault(h, blob)
                k, info = cs.classify(mp, v)
                pairs.append(dict(series=ser, snap=Path(s).stem, obj=i, cls=k, plane=h, **v))
        prev = cur
pickle.dump(dict(pairs=pairs, planes=planes), open(out, 'wb'))
from collections import Counter
print(len(pairs), Counter(p['cls'] for p in pairs), 'distinct planes', len(planes), Counter((p['series'], p['plane'][:6]) for p in pairs))
