"""Drive the wave-5 mothership ($22688 wait, $226ac body, $2279a launched chaser) by a labelled poke and record it.

    python3 mothership_drive.py <snapshot> <ticks> <policy: nofire|autofire> <out.json> [--nopoke] [--trials]

Start snapshot: work/behaviours/g050_s995M.snap (game 50 of the 100-game chain at the start of wave 5: the mothership is
record 18 of 19, wait count $1e). POKES (labelled, applied at every $255d4 arrival, before the tick runs):
  A. ship position := mothership position - 3 x nose (the signed high bytes of matrix words 0, 6, 12), ship velocity := 0, so
     the mothership is inside $b00 of the ship, outside the ship box ($c0) and a shot's third move lands on it;
  B. byte $62a5d := 0 (the ship-hit flag), so the chasers it launches cannot end the run.
--nopoke runs the same capture with no poke at all (control: the natural run).
Events added to shot_capture's set: $22722 launch (the bsr $21722 with A0..A4 loaded), $22666 hit path of the mothership,
$22784 hit path of a launched chaser.
Writes only the out.json (rows as shot_capture.capture returns them, plus 'mship' per row).
"""
import json, os, struct, sys, time

import bh
R = bh.ROOT
import shot as S
import shot_capture as C

C.EV.update({0x22722: 'launch', 0x22666: 'mship_hit', 0x22784: 'mc_hit', 0x2264e: 'mship_kill'})
MS = (0x22688, 0x226ac)

def main():
    a = sys.argv[1:]
    nopoke = '--nopoke' in a
    trials = '--trials' in a
    a = [x for x in a if x not in ('--nopoke', '--trials')]
    snap, N, policy, out = a[0], int(a[1]), a[2], a[3]

    def hook(g, k, row):
        pool = S.unpack_pool(row['pool']) if row['pool'] else []
        ms = [(i, p) for i, p in enumerate(pool) if p[8] in MS]
        row['mship'] = ms[0][1] if ms else None
        if trials:
            # POKE C (labelled; each at one tick, to exercise what the launched chaser's life never reaches): at k = 100 and 200
            # velocity of every live $2279a record := +-$300 on each axis (the clamp, +-$70); at k = 150 and 250 its life := 3
            # (the reversal, which otherwise comes $1ff ticks after the launch). The row's pool bytes are patched to match.
            raw = bytearray(bytes.fromhex(row['pool']))
            for i, p in enumerate(pool):
                if p[8] != 0x2279a:
                    continue
                base = 0x31d54 + 20 * i
                if k in (100, 200):
                    sg = 1 if k == 100 else -1
                    for ax, v in enumerate((0x300 * sg, -0x300 * sg, 0x2c0 * sg)):
                        g.s('poke', addr=base + 6 + 2 * ax, width=2, value=v & 0xffff)
                        raw[20 * i + 6 + 2 * ax:20 * i + 8 + 2 * ax] = (v & 0xffff).to_bytes(2, 'big')
                if k in (150, 250):
                    g.s('poke', addr=base + 12, width=2, value=3)
                    raw[20 * i + 12:20 * i + 14] = (3).to_bytes(2, 'big')
            row['pool'] = raw.hex()
            row['poked'] = k in (100, 150, 200, 250)
        if nopoke or not ms:
            return
        m = ms[0][1]
        n = S.nose(bytes.fromhex(row['matrix']))
        pos = [m[ax] - 3 * n[ax] for ax in range(3)]
        if max(abs(3 * v) for v in n) < 0xd0:          # nose too short for 3n to clear the ship box (+-$c0): lift by $300
            pos[1] += 0x300
        for ax in range(3):
            g.s('poke', addr=0x270b0 + 2 * ax, width=2, value=pos[ax] & 0xffff)
            g.s('poke', addr=0x270b6 + 2 * ax, width=2, value=0)
        g.s('poke', addr=0x62a5d, width=1, value=0)

    t0 = time.time()
    cap = C.capture(policy, N, snap=snap, hook=hook)
    rows = cap['rows']
    cap.pop('map0'); cap.pop('map1'); cap.pop('hmap')
    json.dump(cap, open(out, 'w'))
    cnt = {}
    for r in rows:
        for e in r['ev']:
            cnt[e['e']] = cnt.get(e['e'], 0) + 1
    print(len(rows), 'ticks', round(time.time() - t0), 's; events', cnt)

main()
