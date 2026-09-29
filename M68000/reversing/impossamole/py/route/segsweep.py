"""Rollout search over the start delay of one hop-3 segment, run unpoked with natural_hop3's guard.

    uv run python reversing/impossamole/py/route/segsweep.py <seg name> <start snap> <out dir> [nproc] [w0 w1 wstep]

Idles W frames (24,000 steps) with the guard on, runs the segment function, reports hp lost. Then plays the best W (smallest loss, then the
middle of the longest run of equal-best delays) and saves `<out>/<seg>.snap` and `<seg>.repl` (replayable input).
"""
import sys, os, json
from multiprocessing import Pool
sys.path.insert(0, 'reversing/impossamole/py/route')
import natural_hop3
import route_hop3
from natural_hop3 import NatDriver
from route_driver import *
FRAME = 24000
SEGS = {f.__name__: f for f in route_hop3.SEGS}


def run_seg(snap, name, seg, w, final=None):
    d = NatDriver(snap, name, tick=8000)
    hp0 = d.last.hp
    if w:
        d.hold(NONE, max_steps=w * FRAME, why='start delay')
    if d.last.hp > 0:
        SEGS[seg](d)
    res = dict(seg=seg, w=w, lost=hp0 - d.last.hp, hp=d.last.hp, end=(d.last.wx, d.last.y, d.last.st), steps=d.total_steps,
               pulses=d.pulses, hops=d.hops, nh=len(d.hurts))
    if final:
        d.finish(final)
    else:
        d.close()
    return res


def trial(a):
    snap, seg, out, w = a
    return run_seg(snap, f'{out}/sw/{seg}_w{w:03d}', seg, w)


def main():
    seg, snap, out = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    w0, w1, ws = (int(x) for x in sys.argv[5:8]) if len(sys.argv) >= 8 else (0, 138, 6)
    os.makedirs(f'{out}/sw', exist_ok=True)
    with Pool(n) as p:
        res = []
        for r in p.imap(trial, [(snap, seg, out, w) for w in range(w0, w1, ws)]):
            print(json.dumps(r), flush=True)
            res.append(r)
    alive = [r for r in res if r['hp'] > 0 and r['steps'] > 0]
    best = min(r['lost'] for r in alive)
    ws_ = [r['w'] for r in alive if r['lost'] == best]
    runs, cur = [], [ws_[0]]
    for a, b in zip(ws_, ws_[1:]):
        if b - a <= ws:
            cur.append(b)
        else:
            runs.append(cur); cur = [b]
    runs.append(cur)
    run = max(runs, key=len)
    w = run[len(run) // 2]
    print(f'best loss {best}, run {run[0]}..{run[-1]}, chosen delay {w}', flush=True)
    r = run_seg(snap, f'{out}/{seg}', seg, w, final=f'{out}/{seg}.snap')
    print('played', json.dumps(r), flush=True)


if __name__ == '__main__':
    main()
