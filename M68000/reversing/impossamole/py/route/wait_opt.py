"""Greedy search for wait points inside a hop-3 segment: where a hazard hurts the hero, stand still at P = hurt_wx - D for W frames first.

    uv run python reversing/impossamole/py/route/wait_opt.py <seg> <start snap> <out dir> [nproc]

Runs the segment (natural_hop3's guard, unpoked) with a list of waits [(P, W)]: the first time a plain hold-RIGHT reaches wx >= P grounded, the hero
stands for W frames (24,000 steps), then the segment carries on. For the first hurt not yet handled it tries D in DS and W in WS, keeps the best
total loss, and repeats. Spawn-on-approach enemies are unaffected by a start delay, but a wait at the right place changes when the hero meets
patrolling ones. Output: <out>/<seg>.snap and .repl (replayable input) for the final waits, and a printed summary.
"""
import sys, os, json
from multiprocessing import Pool
sys.path.insert(0, 'reversing/impossamole/py/route')
import natural_hop3
import route_hop3
from natural_hop3 import NatDriver
from route_driver import *
POLICY = os.environ.get('POLICY')          # e.g. BEST: base the driver on the helper's PolicyDriver (policy.py) instead of NatDriver
if POLICY:
    import policy as _pol
    Base = _pol.PolicyDriver
else:
    Base = NatDriver
FRAME = 24000
SEGS = {f.__name__: f for f in route_hop3.SEGS}
DS = (32, 64)
WS = list(range(6, 108, 6))


class WaitDriver(Base):
    def __init__(self, *a, waits=(), **kw):
        self.waits = list(waits)
        self.fired = set()
        if POLICY:
            kw['P'] = _pol.POLICIES[POLICY]
        super().__init__(*a, **kw)

    def hold(self, bits, until=None, max_steps=600_000, **kw):
        if bits == RIGHT:
            pend = [(i, pw) for i, pw in enumerate(self.waits) if i not in self.fired and self.last.wx < pw[0]]
            if pend:
                i, (P, W) = pend[0]
                hit = [False]

                def u2(s):
                    if until is not None and until(s):
                        return True
                    if s.wx >= P and s.st in (0, 1):
                        hit[0] = True
                        return True
                    return False
                reason, s = super().hold(bits, until=u2, max_steps=max_steps, **kw)
                if hit[0] and not (until is not None and until(s)):
                    self.fired.add(i)
                    self.log(ev='wait', P=P, W=W, wx=s.wx, t=self.total_steps)
                    super().hold(NONE, max_steps=W * FRAME, why='wait')
                    return self.hold(bits, until=until, max_steps=max_steps, **kw)
                return reason, s
        return super().hold(bits, until=until, max_steps=max_steps, **kw)


def run_seg(snap, name, seg, waits, final=None):
    d = WaitDriver(snap, name, tick=8000, waits=waits)
    hp0 = d.last.hp
    if d.last.hp > 0:
        SEGS[seg](d)
    res = dict(seg=seg, waits=waits, lost=hp0 - d.last.hp, hp=d.last.hp, end=(d.last.wx, d.last.y, d.last.st), steps=d.total_steps,
               hurts=[h['wx'] for h in (d.hurt_list if POLICY else d.hurts)], fired=sorted(d.fired))
    if final:
        d.finish(final)
    else:
        d.close()
    return res


def trial(a):
    snap, seg, out, waits, tag = a
    return run_seg(snap, f'{out}/wo/{seg}_{tag}', seg, waits)


def score(r):
    return (r['lost'] if r['hp'] > 0 else 99, r['steps'])


def main():
    seg, snap, out = sys.argv[1], sys.argv[2], sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 6
    os.makedirs(f'{out}/wo', exist_ok=True)
    waits = []
    base = trial((snap, seg, out, waits, 'base'))
    print('base', json.dumps(base), flush=True)
    skip = 0
    for it in range(8):
        if base['lost'] == 0:
            break
        hurts = base['hurts']
        h = [x for x in hurts if not waits or x > waits[-1][0]]
        if skip >= len(h):
            break
        target = h[skip]
        cands = []
        for D in DS:
            P = target - D
            if waits and P <= waits[-1][0] + 8:
                continue
            for W in WS:
                cands.append((snap, seg, out, waits + [(P, W)], f'i{it}_D{D}_W{W}'))
        if not cands:
            skip += 1
            continue
        with Pool(n) as p:
            res = list(p.imap(trial, cands))
        best = min(res, key=score)
        print(f'iter {it}: hurt at wx {target}: best {best["lost"]} (base {base["lost"]}) waits {best["waits"]}', flush=True)
        if score(best) < score(base) and best['lost'] < base['lost']:
            base, waits = best, best['waits']
            skip = 0
        else:
            skip += 1
    r = run_seg(snap, f'{out}/{seg}', seg, waits, final=f'{out}/{seg}.snap')
    print('final', json.dumps(r), flush=True)


if __name__ == '__main__':
    main()
