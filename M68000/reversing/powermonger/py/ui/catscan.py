"""Which (byte6) categories occur in which snapshots (bucket walk).  python catscan.py <glob> ... -> per category, snapshots with counts"""
import glob, sys, collections
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parents[4] / 'reversing/powermonger/py'))
from uilib import *
from census import walk
from pm_export import ram_from_snap
found = collections.defaultdict(list)
for pat in sys.argv[1:]:
    for p in sorted(glob.glob(str(ROOT / pat), recursive=True)):
        try:
            r = ram_from_snap(Path(p))
            if r[0x51b66 + 6:0x51b66 + 7] is None: continue
            recs, torn = walk(r)
        except Exception as e:
            continue
        c = collections.Counter((rec[6], rec[7] if rec[6] in (6, 0x14, 0xa, 0xc, 0x1c, 0x1e, 0x2c, 0x20, 0x22, 0x18, 0x16, 0x10) else -1) for _, _, _, rec in recs)
        for (cat, b7), n in c.items(): found[cat].append((Path(p).relative_to(ROOT).as_posix(), b7, n))
for cat in sorted(found):
    print(hex(cat), len(found[cat]), 'snapshots; sample:', found[cat][:3])
