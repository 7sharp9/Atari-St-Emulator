#!/usr/bin/env python3
"""captain_rout.py <out dir> [--log LOG] [--at STEP] [--budget N]: does the captain's posture in one field fight decide
whether the enemy group's lead is killed or routed home as a `$550e` candidate (README "A second side-1 group")?

From a logged land-2 run (default the scripted o1 replay, whose 190M decision sends the field-fight posture fix while
the captain fights side 2's group 1, led by `$041a`), it writes three replay logs that keep every logged order before
STEP and nothing after it, and differ only in the posture order at STEP:
  p2    posture 2 (the logged fix)
  p4    posture 4
  none  no order (the posture the group already had)
then replays each with `loop.py --replay --objs 1e5` to the budget, in parallel, and prints captain_trace.py for
`$041a` over the three. One variable, same snapshot, same budget; the arms hold no later orders, so the captain is
uncommanded after STEP in all three."""
import json, subprocess, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
a = sys.argv[1:]
opt = lambda k, d: a[a.index(k) + 1] if k in a else d
out = Path(a[0]).resolve()
log = ROOT / opt('--log', 'scratchpad/cmd11/so/scripted/o1/decisions.jsonl')
at = int(float(opt('--at', '190e6')))
budget = int(float(opt('--budget', '300e6')))

recs = [json.loads(l) for l in log.read_text().splitlines()]
head = dict(recs[0], budget=budget)
fix = [r for r in recs if r['kind'] == 'applied' and r['step'] == at]
assert len(fix) == 1 and len(fix[0]['actions']) == 1 and fix[0]['actions'][0]['type'] == 22, fix
keep = [r for r in recs[1:] if r['kind'] in ('decision', 'applied') and r['step'] < at]
procs = []
for name, y in (('p2', 2), ('p4', 4), ('none', None)):
    d = out / name; d.mkdir(parents=True, exist_ok=True)
    rows = [head] + keep + [dict(kind='decision', step=at)]
    if y is not None:
        rows.append(dict(kind='applied', step=at, actions=[dict(fix[0]['actions'][0], y=y)]))
    (d / 'in.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in rows))
    for f in ('objs.bin', 'final.snap', 'decisions.jsonl'):
        (d / f).unlink(missing_ok=True)
    procs.append(subprocess.Popen([sys.executable, str(HERE / 'loop.py'), str(d), '--replay', str(d / 'in.jsonl'),
                                   '--objs', '1e5'], cwd=ROOT, stdout=open(d / 'loop.out', 'w'),
                                  stderr=subprocess.STDOUT))
rc = [p.wait() for p in procs]
print('loop.py exit codes', rc)
subprocess.run([sys.executable, str(HERE / 'captain_trace.py'), '041a'] + [str(out / n) for n in ('p2', 'p4', 'none')])
