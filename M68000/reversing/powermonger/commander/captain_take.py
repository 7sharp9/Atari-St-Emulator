#!/usr/bin/env python3
"""captain_take.py <out dir> <snap> <x> <y> [--budget N] [--postures 4,2] [--man 041a]: order side 1's captain to
attack the lord at cell (x, y) from <snap>, once per posture, and report whether side 1 gets a second group
(README "A second side-1 group").

Each arm is a loop.py replay of a two-order log (posture `$16` at step 0, attack `$0c` 400k steps later, then no
orders) with a decision read every 5M steps and `--objs 1e5`; the arms differ only in the posture. Prints per arm:
how the run ended, the first decision step at which side 1 has more than one live group, each side-1 group there,
the target lord's side at the end, and captain_trace.py for the leader-flag man."""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
sys.path.insert(0, str(HERE))
from observe import observe, load          # noqa: E402

a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
out, snap, x, y = Path(a[0]).resolve(), Path(a[1]).resolve().relative_to(ROOT), int(a[2]), int(a[3])
budget = int(float(opt('--budget', '200e6')))
postures = [int(p) for p in opt('--postures', '4,2').split(',')]
man = opt('--man', '041a')

procs = []
for p in postures:
    d = out / f'p{p}'; d.mkdir(parents=True, exist_ok=True)
    rows = [dict(kind='start', snap=str(snap), budget=budget, every=5000000, gap=400000, side=1, take=True),
            dict(kind='applied', step=0, actions=[dict(side=1, take=True), dict(side=1, type=22, x=0, y=p, group=0)]),
            dict(kind='applied', step=400000, actions=[dict(side=1, type=12, x=x, y=y, group=0)])]
    rows += [dict(kind='decision', step=s) for s in range(0, budget, 5000000)]
    (d / 'in.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    for f in ('objs.bin', 'final.snap', 'decisions.jsonl'):
        (d / f).unlink(missing_ok=True)
    procs.append(subprocess.Popen([sys.executable, str(HERE / 'loop.py'), str(d), '--replay', str(d / 'in.jsonl'),
                                   '--objs', '1e5'], cwd=ROOT, stdout=open(d / 'loop.out', 'w'),
                                  stderr=subprocess.STDOUT))
print('loop.py exit codes', [q.wait() for q in procs])
for p in postures:
    d = out / f'p{p}'
    recs = [json.loads(l) for l in (d / 'decisions.jsonl').read_text().splitlines()]
    end = recs[-1]
    two = next((r for r in recs if r['kind'] == 'decision' and len(r['groups']) > 1), None)
    o = observe(load(d / 'final.snap'))
    tgt = [(s, l['idx']) for s, v in o['sides'].items() for l in v['lords'] if l['cell'] == [x, y]]
    print(f'posture {p}: end {end.get("reason")} at {end.get("step", 0) / 1e6:.1f}M; side-1 lords '
          f'{end["totals"]["1"]["lords"]}, group men {end["totals"]["1"]["group_men"]}; target lord (side, idx) {tgt}; '
          f'second group: {"none" if two is None else "at %dM %s" % (two["step"] // 10**6, two["groups"])}')
subprocess.run([sys.executable, str(HERE / 'captain_trace.py'), man] + [str(out / f'p{p}') for p in postures])
