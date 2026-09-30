"""proximity_events.py: events 9 and 7 are pushed every frame while the hero stands next to an object, by the hint handler $009440 (no key pressed).
Counts pushes at $0095c0 (event 9, only when the dedup cache $00e614 says the pair is new), $0095d8 (event 7) and main-loop iterations ($006e44)
over 300,000 steps at the coin (52,23), the TUNNEL lever and in open floor (start), 3 runs each."""
from drv import *
for label, snap in [('coin', ensure('coin')), ('lever', ensure('lever')), ('open floor (start)', START)]:
    res = []
    for i in range(3):
        r = Repl(snap); h = r.hits(300000, 0x95c0, 0x95d8, 0x6e44, 0x9440)
        res.append((h.get(0x95c0, 0), h.get(0x95d8, 0), h.get(0x6e44, 0), h.get(0x9440, 0))); r.close()
    print(f'{label:20s} (event9 pushes, event7 pushes, main-loop iterations, $9440 entries) x3 runs: {res}')
