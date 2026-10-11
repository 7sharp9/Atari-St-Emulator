"""stuck_census.py - are men stuck in the obstacle sweep? Over a chunk series (consecutive snapshots of one run, e.g.
scratchpad/pm148/arms/long/X10G_k44_c<N>.snap, 250M steps apart) list every man record (first 512 records at $51b66,
stride 50, owner byte 5 > 0) that is in a walking mode ($10 advance, $12 on route, $48 sweep, $4a sweep start) in two
consecutive chunks with the same target (20/22) and has not got closer to it (Chebyshev distance in world units, a cell
is 256). Also counts the walking-mode records per chunk. Usage: (from M68000/) uv run python reversing/powermonger/py/fsm/stuck_census.py <prefix> (e.g. .../X10G_k44)."""
import glob
import re
import sys
from pathlib import Path

here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(ROOT / 'tools'))
from disassemble import ram_from_snap  # noqa: E402

WALK = {0x10, 0x12, 0x48, 0x4a}
prefix = sys.argv[1]
snaps = sorted(glob.glob(prefix + '_c*.snap'), key=lambda s: int(re.search(r'_c(\d+)\.snap$', s).group(1)))


def men(s):
    r = ram_from_snap(s)
    sw = lambda a: int.from_bytes(r[a:a + 2], 'big', signed=True)
    out = {}
    for i in range(512):
        o = 0x51b66 + 50 * i
        if r[o + 5] in range(1, 128) and r[o + 31] in WALK and r[o + 6] == 0:
            out[i] = (sw(o + 8), sw(o + 10), sw(o + 20), sw(o + 22), r[o + 31], r[o + 33], r[o + 5], water_on_line(r, o))
    return out


def water_on_line(r, o):
    # cells on the straight line from the man to his target whose terrain bytes ($438ee and the $418ad half, the two
    # bytes $1648e picks between) are both 0, i.e. water to $1648e's dbeq
    sw = lambda a: int.from_bytes(r[a:a + 2], 'big', signed=True)
    x0, y0, x1, y1 = sw(o + 8), sw(o + 10), sw(o + 20), sw(o + 22)
    n = max(abs(x1 - x0), abs(y1 - y0)) // 64 + 1
    seen, wet = set(), 0
    for k in range(n + 1):
        x = x0 + (x1 - x0) * k // n
        y = y0 + (y1 - y0) * k // n
        c = (y >> 8) * 64 + (x >> 8)
        if c in seen or not (0 <= c < 8192):
            continue
        seen.add(c)
        wet += r[0x438ee + c] == 0 and r[0x418ad + c] == 0
    return wet


prev = None
tot_stuck = 0
streak = {}
for s in snaps:
    cur = men(s)
    modes = {}
    for v in cur.values():
        modes[v[4]] = modes.get(v[4], 0) + 1
    stuck = []
    if prev is not None:
        for i, v in cur.items():
            p = prev.get(i)
            if p and p[2:4] == v[2:4]:
                d0 = max(abs(p[2] - p[0]), abs(p[3] - p[1]))
                d1 = max(abs(v[2] - v[0]), abs(v[3] - v[1]))
                if d1 >= d0 - 256:
                    stuck.append('obj%d mode %02x side %d boat %d water-cells-on-line %d pos (%d,%d) target (%d,%d) dist %d -> %d'
                                 % (i, v[4], v[6], v[5] == 0x0a, v[7], v[0] >> 8, v[1] >> 8, v[2] >> 8, v[3] >> 8, d0 >> 8, d1 >> 8))
    tot_stuck += len(stuck)
    ids = {int(re.match(r'obj(\d+)', x).group(1)) for x in stuck}
    streak = {i: streak.get(i, 1) + 1 for i in ids}
    if streak:
        print('   longest streak so far: %d chunks' % max(streak.values()))
    print('%s walking %s stuck %d' % (Path(s).stem, {('%02x' % k): n for k, n in sorted(modes.items())}, len(stuck)))
    for line in stuck:
        print('   ' + line)
    prev = cur
print('total stuck pairs', tot_stuck)
