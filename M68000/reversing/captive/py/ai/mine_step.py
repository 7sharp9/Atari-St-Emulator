"""Step forward (keypad $68, as py/ai/keys.py) from a view_tiles.py snapshot under stserver and count the calls the
step makes into the cell-action code: $985a (party enters a $22/$23 cell), $1073c (tile - 2), $10764 (sound),
$c570 (the area loop after it), $987a (party enters a $36 cell).
Usage: mine_step.py <snap> [<snap> ...]"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cap import R, StServer, snappath  # noqa: E402
ADDRS = [0x985a, 0x1073c, 0x10764, 0xc570, 0x987a]
s = StServer(R)
for snap in sys.argv[1:]:
    s('load', snapshot=snappath(snap))
    tot = {a: 0 for a in ADDRS}
    s('kbd', bytes=[0x68])
    for n, rel in ((60000, True), (300000, False)):
        r = s('hits', steps=n, addrs=ADDRS)
        hits = r.get('hits', r) if isinstance(r, dict) else r
        for h in (hits if isinstance(hits, list) else []):
            tot[int(str(h['addr']).lstrip('$'), 16)] += h['count']
        if rel:
            s('kbd', bytes=[0xe8])
    print(os.path.basename(snap), ' '.join(f'${a:x}:{c}' for a, c in tot.items()), 'raw-last', str(r)[:160])
s.close()
