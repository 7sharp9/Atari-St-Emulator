"""classify_stuck.py - split the men reversing/powermonger/py/fsm/stuck_census.py reports as stuck by the
astar model of the chunk they are stuck in.

Stuck criterion: copied from stuck_census.py (first 512 records at $51b66, owner 1..127, byte 6 == 0, mode in
{$10,$12,$48,$4a} in two consecutive chunks, same target words 20/22, Chebyshev distance not down by a cell).
Classes, from the later chunk's RAM, with the man's own speed byte 16:
  boat      byte 33 == $0a (the $10 probe is skipped; reachability over land does not apply)
  a-twater  the target point samples water ($1648e == 0)
  a-swater  the man's own point samples water
  a         target on land in a different land component (triangle graph)
  b         same component, the straight $10/$12 leg is blocked (A* path given; 'verified' if every leg walks)
  c         same component, the straight $10/$12 leg walks to the target
Each man also gets the tick model's verdict (astar.Map.simulate_walk, 3000 ticks, $10/$12/$4a/$48) and word 28
(non-zero: a follower, whose $4a copies the lead's position into the target).

Usage (from M68000/): uv run python reversing/powermonger/commander/classify_stuck.py [prefix ...]
Default: the six series of the brief. Prints per-series counts, the totals, and every class-c case."""
import glob
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import astar  # noqa: E402

ROOT = astar.ROOT
WALK = {0x10, 0x12, 0x48, 0x4a}
SERIES = ['X10G_k25', 'X10G_k40', 'X10G_k44', 'X10G_k143', 'W5G_k80', 'W5G_k108']


def men(r):
    sw = lambda a: int.from_bytes(r[a:a + 2], 'big', signed=True)
    out = {}
    for i in range(512):
        o = 0x51b66 + 50 * i
        if r[o + 5] in range(1, 128) and r[o + 31] in WALK and r[o + 6] == 0:
            out[i] = dict(x=sw(o + 8), y=sw(o + 10), tx=sw(o + 20), ty=sw(o + 22), mode=r[o + 31], boat=r[o + 33] == 0x0a,
                          side=r[o + 5], speed=r[o + 16], w28=sw(o + 28), prev=r[o + 30], f7=r[o + 7], w42=sw(o + 42),
                          gstate=sw(0x51538 + sw(o + 42)) if sw(o + 42) > 0 else None)
    return out


def classify(mp, v):
    s, t = (v['x'], v['y']), (v['tx'], v['ty'])
    if v['boat']:
        return 'boat', None
    if mp.sample(*t) == 0:
        return 'a-twater', None
    if mp.sample(*s) == 0:
        return 'a-swater', None
    if not mp.reachable(s, t):
        return 'a', None
    ok, _pts, why = mp.leg(s, t, v['speed'], chase=v['prev'] == 0x2e)
    if ok:
        return 'c', None
    wps, ver = mp.path(s, t, v['speed'])
    return 'b', (why, len(wps), ver)


def series(prefix):
    snaps = sorted(glob.glob(prefix + '_c*.snap'), key=lambda s: int(re.search(r'_c(\d+)\.snap$', s).group(1)))
    prev = None
    cnt, cnt_men = Counter(), {}
    ccases, bver = [], Counter()
    sim = Counter()
    bsim = []
    for s in snaps:
        r = astar.ram_from_snap(s)
        cur = men(r)
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
                k, info = classify(mp, v)
                cnt[k] += 1
                cnt_men.setdefault(i, Counter())[k] += 1
                if k in ('b', 'c', 'a', 'a-twater'):
                    arr, tick, pos, modes = mp.simulate_walk((v['x'], v['y']), (v['tx'], v['ty']), v['speed'], 3000,
                                                             chase=v['prev'] == 0x2e)
                    sim[(k, 'arrives' if arr else 'stuck')] += 1
                    if k == 'b' and arr:
                        bsim.append('%s obj%d prev %02x mode %02x arrives t=%d' % (Path(s).stem, i, v['prev'], v['mode'], tick))
                if k == 'b':
                    bver[info[2]] += 1
                if k == 'c':
                    moved = max(abs(v['x'] - p['x']), abs(v['y'] - p['y']))
                    ccases.append('%s obj%d side %d mode %02x prev %02x f7 %02x grp %s/%s moved %d speed %d w28 %d pos (%d,%d) target (%d,%d) cells (%d,%d)->(%d,%d) model-sim %s'
                                  % (Path(s).stem, i, v['side'], v['mode'], v['prev'], v['f7'], v['w42'], v['gstate'], moved, v['speed'], v['w28'], v['x'], v['y'], v['tx'], v['ty'],
                                     v['x'] >> 8, v['y'] >> 8, v['tx'] >> 8, v['ty'] >> 8,
                                     'arrives t=%d' % tick if arr else 'stuck at (%d,%d)' % pos))
        prev = cur
    # per distinct man: his majority class
    per_man = Counter(c.most_common(1)[0][0] for c in cnt_men.values())
    return cnt, per_man, ccases, bver, sim, bsim


if __name__ == '__main__':
    pre = sys.argv[1:] or [str(ROOT / 'scratchpad/pm148/arms/long' / s) for s in SERIES]
    T, TM, TS, TB = Counter(), Counter(), Counter(), Counter()
    allc = []
    allb = []
    for p in pre:
        cnt, per_man, cc, bver, sim, bs = series(p)
        allb += bs
        T += cnt
        TM += per_man
        TS += sim
        TB += bver
        allc += cc
        print('%-10s pairs %4d %s | men %3d %s | b paths verified %d/%d'
              % (Path(p).name, sum(cnt.values()), dict(sorted(cnt.items())), sum(per_man.values()),
                 dict(sorted(per_man.items())), bver[True], sum(bver.values())))
    print('TOTAL pairs %d %s' % (sum(T.values()), dict(sorted(T.items()))))
    print('TOTAL men   %d %s' % (sum(TM.values()), dict(sorted(TM.items()))))
    print('b paths verified %d/%d' % (TB[True], sum(TB.values())))
    print('tick model ($10/$12/$4a/$48, 3000 ticks) by class:', dict(sorted(TS.items())))
    print('class b pairs the tick model says arrive (%d):' % len(allb))
    for c in allb:
        print('   ' + c)
    print('class c cases (%d):' % len(allc))
    for c in allc:
        print('   ' + c)
