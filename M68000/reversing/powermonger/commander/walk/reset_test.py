"""reset_test.py - for the pairs census_cmp.py calls 'plain arrives, game redispatched first': the observed gaps between
outside writes (in own-tick units), and walker.simulate with a reset to mode $10 every R ticks (R = the man's median
and max observed gap). Usage: reset_test.py bc_full.json"""
import json, os, re, statistics, sys
from collections import Counter
from pathlib import Path
HERE = Path(__file__).resolve().parent
import os as _os
WORK = next(p for p in HERE.parents if (p / 'tools' / 'rdis.py').exists()) / _os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'walk'
WORK.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(HERE))
import walker, census_run, census_cmp
from trace_cmp import own
d = json.load(open(sys.argv[1]))
res = {(r['snap'], r['obj']): r for r in json.load(open(WORK / 'census_cmp.json'))}
T = Counter()
gaps_all = []
for snap, grp in census_run.jobs(d):
    stem = '%s_%d' % (Path(snap).stem, grp[0]['obj'])
    err = WORK / 'runs' / (stem + '.err')
    sel = [x for x in grp if res[(Path(snap).stem, x['obj'])]['verdict'].startswith('plain arrives, game redis')]
    if not sel:
        continue
    cls = census_cmp.events(err, [x['obj'] for x in sel])
    mp = walker.astar.Map(snap)
    for x in sel:
        t, outs = 0, []
        for c in cls[x['obj']]:
            if all(own(pc) for (_s, pc, *_r) in c):
                if any(off not in (0, 1, 2, 3, 14) for (_s, _pc, off, _n, _v) in c):
                    t += 1
            else:
                if not outs or outs[-1] != t:
                    outs.append(t)
        gaps = [b - a for a, b in zip(outs, outs[1:])]
        gaps_all += gaps
        st = walker.decode(bytes.fromhex(x['rec']))
        verdicts = []
        for name, R in (('first', outs[0] if outs else None), ('median', int(statistics.median(gaps)) if gaps else None),
                        ('max', max(gaps) if gaps else None)):
            if not R:
                verdicts.append((name, None))
                continue
            resets = set(range(R, 3000, R)) if name != 'first' else set(range(outs[0], 3000, max(gaps or [3000])))
            arr, tick, _s = walker.simulate(mp, st, 3000, resets=resets)
            verdicts.append((name, R, arr, tick))
            T[(name, 'arrives' if arr else 'stuck')] += 1
        print(Path(snap).stem, x['obj'], 'prev %02x' % x['prev'], 'plain tick', x['full_tick'], 'first out', outs[:1],
              'gaps median/max', (statistics.median(gaps), max(gaps)) if gaps else None, verdicts)
print(T)
print('all gaps: n %d median %s max %s' % (len(gaps_all), statistics.median(gaps_all), max(gaps_all)))
