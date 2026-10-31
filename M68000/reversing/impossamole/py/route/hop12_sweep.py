"""Start-delay rollout over a run of route_hop1_2.py segments.

    uv run python reversing/impossamole/py/route/hop12_sweep.py <start snap> <out dir> <seg,seg,...> <w0> <w1> <wstep> [nproc] [--set JSON]

For each W: resume the start snapshot under the BEST guard (with --set overrides), idle W frames (24,000 steps) after the first segment's own
wait for the hero, run the segments in order in ONE driver, print hp lost per segment and the end state. Nothing is saved but the logs.
"""
import json, os, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import route_hop1_2 as R
from route_driver import *
FRAME = 24000


def trial(a):
    snap, out, segs, w, st = a
    R.SET.update(st)     # workers are spawned, not forked: pass the overrides explicitly
    d = R.make_driver('BEST', snap, f'{out}/w{w:03d}')
    fns = {f.__name__: f for f in R.SEGS}
    res = dict(w=w, hp=[d.last.hp])
    R.DELAY = w * FRAME
    for n in segs:
        fns[n](d)
        res['hp'].append(d.last.hp)
        if d.last.hp <= 0:
            break
    res.update(lost=res['hp'][0] - d.last.hp, end=(d.last.wx, d.last.y, d.last.st), steps=d.total_steps)
    d.close()
    return res


if __name__ == '__main__':
    a = sys.argv[1:]
    if '--set' in a:
        R.SET.update(json.loads(a[a.index('--set') + 1])); i = a.index('--set'); del a[i:i + 2]
    snap, out, segs = a[0], a[1], a[2].split(',')
    w0, w1, ws = int(a[3]), int(a[4]), int(a[5])
    n = int(a[6]) if len(a) > 6 else 2
    os.makedirs(os.path.join(ROOT, out), exist_ok=True)
    with Pool(n) as p:
        for r in p.imap(trial, [(snap, out, segs, w, R.SET) for w in range(w0, w1, ws)]):
            print(json.dumps(r), flush=True)
