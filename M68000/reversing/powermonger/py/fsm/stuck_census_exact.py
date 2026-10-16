"""stuck_census_exact.py - stuck_census.py with the game's own water test in place of the "both terrain bytes 0" cell
heuristic.

Stuck criterion: unchanged from stuck_census.py (first 512 records at $51b66, owner byte 5 in 1..127, byte 6 == 0, mode
$10/$12/$48/$4a in two consecutive chunks, same target words 20/22, Chebyshev distance not down by a cell = 256 units).
Chunks whose own run executed no $6522 (stuck_classes.frozen(): the game is over, RAM frozen at the main menu) are
skipped, and a frozen chunk breaks the pair chain (a pair needs two consecutive live chunks).

Water test. Every caller of $1648e ($14c58 $14d0a $14d42 $14de6 $14f86 $1591c $161ea; raw scan of $10a6..$1c48a for
bsr.w / bsr.s / jsr / jmp d16(PC) and abs.l) branches only on the Z flag of the routine's closing move.b, so
"impassable" is exactly "the sampled triangle byte is 0" (tools/pm_fsm_ref.terrain_sample). Per stuck man (later
chunk's RAM, his own speed byte 16):
  leg      the straight $10/$12 leg replayed by astar.Map.leg ($164bc legs, the $14f82 dbeq probe of `dwell` points,
           the $161c4 clamp and veto per step, the $14fdc target snap): open / probe-water / step-water / target-water /
           replan-cap. A Boat carrier (byte 33 == $0a) skips the probe ($14f66) and reads 'boat'.
  wet      the ghost walk: the same $164bc legs followed to the target with no veto, every probe and step point sampled;
           the number of distinct water triangles ($1648e == 0) it touches. The exact counterpart of the heuristic's
           water-cells-on-line.
  tick     the mode one $10 tick leaves from his current state (h_mode10, gated by gate_probe.py): $4a = the probe of the
           first `dwell` points met water now; the leg verdict also covers the later $164bc legs.
  heur     stuck_census.py's count (cells on a 64-unit straight-line raster with both bytes 0), printed for comparison.

Usage (from M68000/): uv run python reversing/powermonger/py/fsm/stuck_census_exact.py <prefix> [prefix ...]
(e.g. scratchpad/pm148/arms/long/X10G_k25). Prints each pair, then per-series and total tallies."""
import glob
import re
import sys
from collections import Counter
from pathlib import Path

here = Path(__file__).resolve()
ROOT = next(p for p in here.parents if (p / 'tools' / 'rdis.py').exists())
GAME = ROOT / 'reversing' / 'powermonger'
sys.path.insert(0, str(GAME / 'commander'))
sys.path.insert(0, str(GAME / 'py' / 'arms'))
import astar  # noqa: E402
import stuck_classes  # noqa: E402
from pm_fsm_ref import s16  # noqa: E402

WALK = {0x10, 0x12, 0x48, 0x4a}


def men(r):
    sw = lambda a: int.from_bytes(r[a:a + 2], 'big', signed=True)
    out = {}
    for i in range(512):
        o = 0x51b66 + 50 * i
        if r[o + 5] in range(1, 128) and r[o + 31] in WALK and r[o + 6] == 0:
            out[i] = dict(x=sw(o + 8), y=sw(o + 10), tx=sw(o + 20), ty=sw(o + 22), mode=r[o + 31], boat=r[o + 33] == 0x0a,
                          side=r[o + 5], speed=r[o + 16], prev=r[o + 30], heur=water_on_line(r, o))
    return out


def water_on_line(r, o):
    # stuck_census.py's heuristic, verbatim
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


def ghost_points(mp, v, max_replans=64):
    """every point the $10/$12 straight leg samples on the way to the target, with no veto: per $164bc leg the `dwell`
    probe points P + k*step (unclamped, $14f82) and the `dwell` clamped step points ($14ff8 -> $161c4), then the target
    when $164bc says reached ($14fdc)."""
    x, y, tx, ty = v['x'], v['y'], v['tx'], v['ty']
    pts = []
    for _ in range(max_replans):
        sx, sy, dwell, _h = mp._step(x, y, tx, ty, v['speed'])
        if dwell == 0:
            pts.append((tx & 0xffff, ty & 0xffff))
            break
        px, py = x, y
        for _k in range(dwell):
            px, py = (px + sx) & 0xffff, (py + sy) & 0xffff
            pts.append((px, py))
        for _k in range(dwell):
            x, y = astar.ref._clamp((x + sx) & 0xffff, (y + sy) & 0xffff)
            pts.append((x, y))
    return pts


def exact(mp, v):
    pts = ghost_points(mp, v)
    wet = {mp.node(x, y) for x, y in pts if mp.sample(x, y) == 0}
    edge = sum(1 for x, y in pts if mp.node(x, y) is None)
    if v['boat']:
        verdict = 'boat'
    else:
        ok, _p, why = mp.leg((v['x'], v['y']), (v['tx'], v['ty']), v['speed'], chase=v['prev'] == 0x2e)
        verdict = 'open' if ok else why[0]
    return verdict, len(wet), edge, len(pts)


def tick(ram, i):
    """one mode-$10 tick from the man's current state (tools/pm_fsm_ref.h_mode10, gated against callcap $14f08 by
    gate_probe.py): the mode it leaves, $4a when the $14f82 probe meets water; None where the model stops (the $15302
    chase contact or the $1518a group hand-off)."""
    m = astar.ref.Mem(ram)
    A1 = 0x51b66 + 50 * i
    try:
        astar.ref.h_mode10(m, A1, m.wu(A1 + 8), m.wu(A1 + 10))
    except AssertionError:
        return None
    return m.bu(A1 + 31)


def census(prefix):
    snaps = sorted(glob.glob(prefix + '_c*.snap'), key=lambda s: int(re.search(r'_c(\d+)\.snap$', s).group(1)))
    prev = None
    tally = Counter()
    rows = []
    nlive = nfro = 0
    for s in snaps:
        st = stuck_classes.frozen(Path(s))
        if st != 'live':
            nfro += 1
            prev = None
            continue
        nlive += 1
        mp = astar.Map(s)
        cur = men(mp.ram)
        if prev is not None:
            for i, v in cur.items():
                p = prev.get(i)
                if not p or (p['tx'], p['ty']) != (v['tx'], v['ty']):
                    continue
                d0 = max(abs(p['tx'] - p['x']), abs(p['ty'] - p['y']))
                d1 = max(abs(v['tx'] - v['x']), abs(v['ty'] - v['y']))
                if d1 < d0 - 256:
                    continue
                verdict, wet, edge, npts = exact(mp, v)
                tm = tick(mp.ram, i)
                tally['tick %s' % ('?' if tm is None else '%02x' % tm if tm in (0x4a, 0x12, 0x10, 0) else 'reached')] += 1
                tally['tick 4a & leg water'] += tm == 0x4a and verdict.endswith('water')
                tally['tick not 4a & leg water'] += tm != 0x4a and verdict.endswith('water')
                hb, eb = v['heur'] > 0, verdict in ('probe-water', 'step-water', 'target-water')
                tally['pairs'] += 1
                tally['verdict ' + verdict] += 1
                tally['heur>0'] += hb
                tally['wet>0'] += wet > 0
                tally['leg blocked by water'] += eb
                tally['heur>0 & leg water'] += hb and eb
                tally['heur>0 & leg not water'] += hb and not eb
                tally['heur=0 & leg water'] += (not hb) and eb
                tally['heur=0 & wet>0'] += (not hb) and wet > 0
                tally['heur>0 & wet=0'] += hb and wet == 0
                tally['heur==wet'] += v['heur'] == wet
                rows.append('%s obj%d mode %02x side %d boat %d heur %d wet %d leg %s tick %s edgepts %d pts %d pos (%d,%d) target (%d,%d)'
                            % (Path(s).stem, i, v['mode'], v['side'], v['boat'], v['heur'], wet, verdict, '-' if tm is None else '%02x' % tm, edge, npts,
                               v['x'] >> 8, v['y'] >> 8, v['tx'] >> 8, v['ty'] >> 8))
        prev = cur
    return tally, rows, nlive, nfro


if __name__ == '__main__':
    T = Counter()
    for pf in sys.argv[1:]:
        t, rows, nlive, nfro = census(pf)
        for r in rows:
            print('   ' + r)
        print('%s: %d live chunks, %d frozen/unknown skipped; %s' % (Path(pf).name, nlive, nfro, dict(sorted(t.items()))))
        T.update(t)
    print('TOTAL', dict(sorted(T.items())))
