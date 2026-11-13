"""gate_ticks.py: rollout.py's tick mode gives the unstubbed game's outcome.

    gate_ticks.py [--mid DIR] [--decisions 40000000,80000000,120000000] [--ticks 120] [--long 40000000:1000] [--par 5]

Decision points and candidates come from a finished `loop.py --policy rollout` run (default: gate_rollout.sh's
<CMD_WORK>/rollout/mid): <mid>/dec/<step>.snap and the candidates' action lists in <mid>/decisions.jsonl. For each
decision every candidate runs twice in tick mode from the same snapshot with the same schedule, once with nothing
stubbed and once with the default stub ($f898); the one variable is the stub. A candidate is equal when its outcome
(clock, ticks run, land end, per-side totals, score, observation hash) is the same in both. --long adds one decision
at a longer horizon. The control stubs $3e06 (a simulation routine: armies eat) on the first decision and must
change at least one candidate's outcome. Prints `gate_ticks: a/b equal` and the control line; exit 1 unless every
candidate is equal and the control differs.

Also printed, not gated: the step-mode score and choice the loop recorded for each decision beside the tick-mode
ones (different horizon ends and poke phases, so they need not agree), and steps and wall time per arm.
"""
import json, os, sys, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from rollout import rollout, ROOT, STUBS        # noqa: E402

KEYS = ('clock', 'ticks', 'land_end', 'sides', 'force', 'score', 'obs_hash', 'captain', 'ratio')


def main(argv):
    a = list(argv)
    opt = lambda name, d: (a.pop(a.index(name) + 1), a.remove(name))[0] if name in a else d
    mid = Path(opt('--mid', str(ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'rollout' / 'mid')))
    decs = [int(x) for x in opt('--decisions', '40000000,80000000,120000000').split(',')]
    ticks = int(opt('--ticks', '120'))
    long = opt('--long', '40000000:1000')
    par = int(opt('--par', '5'))
    side = int(opt('--side', '3'))
    work = ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'ticks'
    rec = {}
    for l in open(mid / 'decisions.jsonl'):
        r = json.loads(l)
        if r.get('kind') == 'decision' and 'rollout' in r:
            rec[r['step']] = r['rollout']
    jobs = [(d, ticks) for d in decs]
    if long:
        d, t = long.split(':')
        jobs.append((int(d), int(t)))
    ok = total = 0
    for d, T in jobs:
        snap = mid / 'dec' / f'{d}.snap'
        cands = [dict(name=c['name'], actions=c['actions']) for c in rec[d]['cands']]
        res = {}
        for arm, stubs in (('noskip', ()), ('skip', STUBS)):
            t = time.time()
            res[arm], best = rollout(snap, side, cands, 0, par=par, out=work / f'{d}_{T}_{arm}', baseline=False,
                                     ticks=T, stubs=stubs)
            res[arm + '_best'], res[arm + '_wall'] = cands[best]['name'], time.time() - t
        for x, y in zip(res['noskip'], res['skip']):
            same = all(x[k] == y[k] for k in KEYS)
            total += 1; ok += same
            print(f"D={d} T={T} {x['name']:13} {'equal ' if same else 'DIFFER'} score {x['score']} / {y['score']}  "
                  f"steps {x['steps']} / {y['steps']} ({x['steps'] / max(y['steps'], 1):.2f}x)  hash {x['obs_hash']} / {y['obs_hash']}")
        up = os.popen('uptime').read().strip().split('load averages:')[-1].strip()
        print(f"D={d} T={T} best noskip {res['noskip_best']} skip {res['skip_best']}; wall {res['noskip_wall']:.1f} s / "
              f"{res['skip_wall']:.1f} s for {len(cands)} candidates at par {par} (load {up}); step mode N={rec[d]['N']}: best "
              f"{rec[d]['best']}, scores {[(c['name'], c['score']) for c in rec[d]['cands']]}")
    d = decs[0]
    cands = [dict(name=c['name'], actions=c['actions']) for c in rec[d]['cands']]
    base, _ = rollout(mid / 'dec' / f'{d}.snap', side, cands, 0, par=par, out=work / f'{d}_{ticks}_noskip', baseline=False,
                      ticks=ticks, stubs=())
    neg, _ = rollout(mid / 'dec' / f'{d}.snap', side, cands, 0, par=par, out=work / f'{d}_{ticks}_neg3e06', baseline=False,
                     ticks=ticks, stubs=(0x3e06,))
    ndiff = sum(any(x[k] != y[k] for k in KEYS) for x, y in zip(base, neg))
    print(f'control: stub $3e06 changes {ndiff}/{len(cands)} candidate outcomes at D={d} T={ticks}')
    print(f'gate_ticks: {ok}/{total} equal')
    return 0 if ok == total and ndiff > 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
