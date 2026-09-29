"""Cross the four pits from any state before pit 1: per pit, sweep the take-off delay in a rollout search, take the middle of the longest
zero-loss window, play it, save the snapshot and a replayable .repl for that pit.

    uv run python reversing/impossamole/py/route/auto_pits.py <start snap> <out dir> [nproc] [pits, default 1234]

The delay depends on the crocodile's phase, which depends on when the hero arrives, so it has to be searched again for any different arrival.
The result is recorded input (found by search, replayable byte-identically), not a policy that reads the crocodile before it decides.
"""
import sys, os, json
from multiprocessing import Pool
sys.path.insert(0, 'reversing/impossamole/py/route')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pits
from pits import *


def pick(results, pit):
    """Middle of the longest run of consecutive zero-loss delays (delays are sorted)."""
    good = [r['w'] for r in results if r['ok'] and r['lost'] == 0]
    if not good:
        best = min(results, key=lambda r: (r['lost'], not r['ok']))
        return best['w'], None
    runs, cur = [], [good[0]]
    for a, b in zip(good, good[1:]):
        if b - a <= 6:
            cur.append(b)
        else:
            runs.append(cur); cur = [b]
    runs.append(cur)
    run = max(runs, key=len)
    return run[len(run) // 2], (run[0], run[-1])


def play_one(snap, out_prefix, pit, w):
    d = Driver(snap, out_prefix, tick=6000, hp_floor=-1)
    hp0 = d.last.hp
    take, edge = PITS[pit]
    if pit in pits.NOCROC:
        take += w
        w = 0
    if d.last.wx < take:
        walk_to(d, take)
    if w:
        d.idle(w * FRAME)
    ok, trace = cross(d, pit, stop_on_loss=False)
    end = out_prefix + '.snap'
    d.finish(end)
    return ok, hp0 - d.last.hp, trace, end


def main():
    start, out = sys.argv[1], sys.argv[2]
    nproc = int(sys.argv[3]) if len(sys.argv) > 3 else 6
    which = [int(c) for c in (sys.argv[4] if len(sys.argv) > 4 else '1234')]
    os.makedirs(out, exist_ok=True)
    snap = start
    total = 0
    for pit in which:
        rng = range(0, 31, 2) if pit in pits.NOCROC else range(0, 138, 6)
        with Pool(nproc) as p:
            res = list(p.imap(trial, [(snap, pit, w) for w in rng]))
        w, win = pick(res, pit)
        print(f'pit {pit}: zero-loss window {win}, chosen {"offset" if pit in pits.NOCROC else "delay"} {w}', flush=True)
        ok, lost, trace, snap = play_one(snap, f'{out}/pit{pit}', pit, w)
        total += lost
        print(f'pit {pit}: ok={ok} lost={lost} trace={trace}', flush=True)
    print('total lost', total, 'end snapshot', snap)


if __name__ == '__main__':
    main()
