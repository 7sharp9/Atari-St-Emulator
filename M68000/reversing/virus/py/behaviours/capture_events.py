"""Generic capture of a natural (unpoked) run with extra event breakpoints, for the two-hit pursuer and the provoking checks.

    python3 capture_events.py <snapshot> <ticks> <out.json> [policy] [--lifepoke]      (policy default auto)

Adds to shot_capture's event set: $22164 p2_hit1 (the first-hit path of $2202c), $20206 provoke (the store of $21f00 into a patrol's +16,
with A0 = the record), $201b4 provoke_entry (the scan). For p2_hit1 and provoke the event carries the record at A0 or A6-20.
Writes only the out.json (rows as shot_capture.capture returns them, without the map dumps)."""
import json, os, sys, time

import bh
R = bh.ROOT
import shot_capture as C

C.EV.update({0x22164: 'p2_hit1', 0x20206: 'provoke', 0x201b4: 'provoke_entry'})
# shot_capture records A6-20 for 'kill' and 'ship_hit' only; wrap its register reads for the new events through the PATHS hook is not
# available, so the record is recovered from the pool rows afterwards (the pool at the arrival before and after).
snap, N, out = sys.argv[1], int(sys.argv[2]), sys.argv[3]
lifepoke = '--lifepoke' in sys.argv
policy = ([a for a in sys.argv[4:] if a != '--lifepoke'] or ['auto'])[0]
import struct, shot as S

def hook(g, k, row):
    """--lifepoke (labelled POKE): at k in 150, 300, 450 the life word of every live chaser ($21afe) := 3, so its reversal (every $1ff
    ticks, never reached by a chaser the player kills sooner) happens within 3 ticks; the row's pool bytes are patched to match."""
    if not lifepoke or k not in (150, 300, 450) or not row['pool']:
        return
    raw = bytearray(bytes.fromhex(row['pool']))
    for i, p in enumerate(S.unpack_pool(row['pool'])):
        if p[8] == 0x21afe:
            g.s('poke', addr=0x31d54 + 20 * i + 12, width=2, value=3)
            raw[20 * i + 12:20 * i + 14] = (3).to_bytes(2, 'big')
    row['pool'] = raw.hex(); row['poked'] = True

t0 = time.time()
cap = C.capture(policy, N, snap=snap, hook=hook if lifepoke else None)
for k in ('map0', 'map1', 'hmap'):
    cap.pop(k)
json.dump(cap, open(out, 'w'))
cnt = {}
for r in cap['rows']:
    for e in r['ev']:
        cnt[e['e']] = cnt.get(e['e'], 0) + 1
print(len(cap['rows']), 'ticks', round(time.time() - t0), 's', cnt)
