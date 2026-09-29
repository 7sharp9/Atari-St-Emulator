"""Per-segment route report from the driver logs (segs/*.log).

    uv run python reversing/impossamole/py/route/route_report.py > route_report.txt

For each segment: steps, start and end position, the input phases (joystick byte, why-label, first/last wx, y, state,
tick count), labelled pokes and a hazard census (health drops attributed to the objects within 40 px, by animation
pointer). Object anim pointers: $2219a/$22194 bee (chaser, slots 7/8), $22132 crocodile, $21fee/$2201e/$22010/$21fe0/
$21fe4 ground/water enemies, $2270a static prop.
"""
import collections, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_driver import ROOT, STATE_NAMES
import route_hop3 as R

D = os.path.join(ROOT, R.BASE)
BEE = {'0002219a', '00022194'}


def main():
    total_hurts = collections.Counter()
    for f in R.SEGS:
        n = f.__name__
        ticks, hurts, pokes = [], [], []
        end = None
        for l in open(os.path.join(D, 'segs', n + '.log')):
            e = json.loads(l)
            if e.get('ev') == 'hurt':
                hurts.append(e)
            elif e.get('ev') == 'poke':
                pokes.append(e)
            elif e.get('ev') == 'end':
                end = e
            elif 't' in e:
                ticks.append(e)
        print(f'== {n}: {end["steps"]} steps, {len(ticks)} ticks, {len(hurts)} health drops, {len(pokes)} pokes')
        print(f'   start x={ticks[0]["x"]} y={ticks[0]["y"]} wx={ticks[0]["wx"]} cam={ticks[0]["cam"]:#x} | '
              f'end x={ticks[-1]["x"]} y={ticks[-1]["y"]} wx={ticks[-1]["wx"]} cam={ticks[-1]["cam"]:#x} blk={ticks[-1]["blk"]}')
        # phases: consecutive ticks with same (in, why)
        ph = []
        for t in ticks:
            k = (t['in'], t['why'])
            if ph and ph[-1]['k'] == k:
                ph[-1]['n'] += 1; ph[-1]['last'] = t
            else:
                ph.append(dict(k=k, n=1, first=t, last=t))
        for p in ph:
            a, b = p['first'], p['last']
            print(f'   kbd {p["k"][0]}  {p["k"][1]:<28} {p["n"]:>4} ticks  t={a["t"]}..{b["t"]}  wx {a["wx"]}->{b["wx"]}  y {a["y"]}->{b["y"]}'
                  f'  st {STATE_NAMES.get(a["st"], a["st"])}->{STATE_NAMES.get(b["st"], b["st"])}')
        for p in pokes:
            print(f'   POKE {p["cmd"]} at step {p["steps"]}: {p["label"]}')
        c = collections.Counter()
        for h in hurts:
            others = sorted({n_['anim'] for n_ in h['near']} - {'0002270a'})
            k = 'bee' if BEE & set(others) else ('other' if others else 'none within 40px')
            desc = ','.join('$' + a[-5:] for a in others if a not in BEE)
            c[(k, desc)] += 1
            total_hurts[(k, desc)] += 1
        for (k, desc), v in c.most_common():
            print(f'   hurt x{v}: {k} {desc}')
    print('== totals')
    for (k, desc), v in total_hurts.most_common():
        print(f'   hurt x{v}: {k} {desc}')


if __name__ == '__main__':
    main()
