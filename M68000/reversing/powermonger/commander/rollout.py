"""rollout.py: the exact-rollout forecaster (commander README "Forecaster", plan step 5's first half).

    rollout.py <snap> <cands.json|-> --side K --steps N [--gap G] [--par P] [--out DIR] [--keep]

Given a snapshot (a decision point, e.g. one loop.py --policy rollout saved with `snap` before its pokes), a side and K candidate
action lists (act.from_json format), each candidate runs in its own emulator process (`resume <snap> repl`, driven
by commander/loop.py's Emu over pipes), at most P at once. A candidate's i-th action is poked at step i*G, as
loop.py schedules one decision's actions (after an `m $58010 $40` read so act.Poker fills the longwords' neighbour
bytes from current RAM, exactly as loop.py does); stepping is `bp d2c8 <n>`, so a land end ($d2c8, strategy.md
"How a land ends") stops the rollout at its step. At step N (or the land end) the process saves a snapshot and the
outcome is read from it with observe.py.

cands.json: a list of {"name": str, "actions": [...]} (or bare action lists). A no-order baseline {"name": "none",
"actions": []} is added when no candidate has an empty list.

Outcome per candidate: per side lords, men at home, group men, lord food, group food, groups alive, the game's own
force total $57fba[side].word0, the ratio $57fce, the land-end flag and step, and a scalar score.

Score (for side s): F_s / E with F a side's force as $57fba[*].word0 holds it at the end of a tick (men at home of
lords with men + group men, strategy.md "$d322 + $3e06 -> $57fba") and E = sum of the other sides' F + 1. F is
recomputed from observe.py's totals (men_home + group_men), not read from $57fba: the word is rebuilt from zero every
tick ($d322 zeroes it, adds the lords, then $3e06 adds the groups), so a snapshot taken mid-rebuild reads a torn value.
On the loop agent's run1 decisions the two agree at 795 of 800 side-reads; the 5 others are torn reads (e.g. step
370M: raw = men at home alone). The raw word is kept in the output as raw_57fba. This is the continuous core of the
game's own verdict formula `$57fce = min(4, (2*F_s + E/4) / E)` ($d23a, which is computed for the local side only):
the ratio is a clamped, floored, monotone function of F_s/E, so maximising F_s/E maximises the ratio the verdict
would read if s were local, without the clamp and floor that make most short-horizon candidates tie at 0. Ties
(equal F_s/E) are broken by own lords, then by the candidate's order in the list (the first is the scripted choice).
`ratio_as_local` reports the clamped formula itself for s.

For the local side the score also values the captain, the one thing that loses a land (strategy.md "How a land ends":
`$d23a` posts the defeat when group 0's owner word drops to 0). A land end inside the horizon is a win when the ratio
read at `$d2c8` is 4 (score WIN + F/E) and a defeat otherwise (score LOSS); a captain group with owner <= 0 is a defeat.
Otherwise the score is F/E - CAP_W * (captain men lost / captain men at the start) - STARVE_W when the captain group
ends the horizon with men and no food. The weights are heuristics, not derived from the game: on campaign land 1 the
F/E policy let the captain group sit idle until its food ran out and its men starved (cmd2/l1/rollout, 34 men at
350M, food 0 at 450M, dissolved at 725M with side 1 ahead 57 to 44).
"""
import json, os, struct, sys, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ['M68000_ROOT']) if os.environ.get('M68000_ROOT') else \
    next(d for d in HERE.parents if (d / 'tools' / 'rdis.py').exists())
CMD = ROOT / 'reversing' / 'powermonger' / 'commander'
sys.path.insert(0, str(CMD))
from observe import observe, load          # noqa: E402
from act import from_json                  # noqa: E402
from loop import Emu, obs_hash             # noqa: E402

F57FBA = 0x57fba                           # strategy.md: 5 x 4-byte per-side force totals, word0 = men
WIN, LOSS = 10.0, -1.0                     # land end inside the horizon, local side only
CAP_W, STARVE_W = 1.0, 0.5                 # captain men lost (fraction of the start), captain group starving


def captain(obs, side):
    """The local side's captain group (group 0): (owner, men, food), or None when side is not the local side."""
    if side != obs['local_side'] or side not in obs['sides']:
        return None
    g = obs['sides'][side]['groups'][0]
    return g['owner'], g['men'], g['food']


def summary(R, side, cap0=None, land_end=False):
    obs = observe(R)
    raw = [struct.unpack_from('>H', R, F57FBA + 4 * s)[0] for s in range(5)]
    F = [0] * 5
    sides = {}
    for s, v in obs['sides'].items():
        t = v['totals']
        F[int(s)] = t['men_home'] + t['group_men']
        sides[int(s)] = dict(lords=t['lords'], men_home=t['men_home'], group_men=t['group_men'], lord_food=t['lord_food'],
                             group_food=t['group_food'], groups_alive=t['groups_alive'], force=F[int(s)],
                             raw_57fba=raw[int(s)])
    E = sum(F) - F[side] + 1
    score = F[side] / E
    cap = captain(obs, side)
    if cap is not None:
        owner, men, food = cap
        if land_end:
            score = WIN + score if obs['ratio'] == 4 else LOSS
        elif owner <= 0:
            score = LOSS
        else:
            if cap0 and cap0[1] > 0:
                score -= CAP_W * max(0, cap0[1] - men) / cap0[1]
            if men > 0 and food == 0:
                score -= STARVE_W
    return obs, dict(clock=obs['clock'], ratio=obs['ratio'], sides=sides, force=F,
                     ratio_as_local=min(4, (2 * F[side] + E // 4) // E), captain=cap,
                     score=round(score, 6), obs_hash=obs_hash(obs))


def run_one(snap, side, name, actions, steps, gap, out, keep=True, cap0=None):
    """One candidate: returns its outcome dict."""
    t0 = time.time()
    emu = Emu(snap, out / f'{name}.err')
    tstart = time.time() - t0
    sched = {}
    for i, ac in enumerate(actions):
        sched.setdefault(i * gap, []).append(ac)
    clock, end, endstep = 0, False, None
    try:
        while True:
            if clock in sched:
                emu.mem(0x58010, 0x40)
                emu.poke(from_json(emu.ram, sched.pop(clock)))
            if clock >= steps:
                break
            nxt = min([steps] + [s for s in sched if s > clock])
            n, hit = emu.run(nxt - clock)
            clock += n
            if hit:
                end, endstep = True, clock
                break
        sp = out / f'{name}.snap'
        emu.save(sp)
    finally:
        emu.close()
    R = load(sp)
    obs, res = summary(R, side, cap0, end)
    if not keep:
        sp.unlink()
    wall = time.time() - t0
    return dict(name=name, actions=actions, steps=clock, land_end=end, land_end_step=endstep,
                wall_s=round(wall, 2), startup_s=round(tstart, 2),
                steps_per_s=round(clock / max(wall - tstart, 1e-9)), **res, snap=str(sp) if keep else None)


def rollout(snap, side, cands, steps, gap=400_000, par=4, out=None, keep=True, baseline=True):
    """cands: list of {"name", "actions"}; returns the outcomes in candidate order plus the index of the best."""
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    cands = [c if isinstance(c, dict) else dict(name=f'c{i}', actions=c) for i, c in enumerate(cands)]
    names = [c['name'] for c in cands]
    assert len(set(names)) == len(names), f'candidate names must be unique (snapshot file names): {names}'
    if baseline and not any(not c['actions'] for c in cands) and 'none' not in names:
        cands = cands + [dict(name='none', actions=[])]
    cap0 = captain(observe(load(snap)), side)
    with ThreadPoolExecutor(max_workers=par) as ex:
        futs = [ex.submit(run_one, snap, side, c['name'], c['actions'], steps, gap, out, keep, cap0) for c in cands]
        res = [f.result() for f in futs]
    best = max(range(len(res)), key=lambda i: (res[i]['score'], res[i]['sides'][side]['lords'], -i))
    return res, best


def main(argv):
    a = list(argv)
    opt = lambda name, d: (a.pop(a.index(name) + 1), a.remove(name))[0] if name in a else d
    flag = lambda name: (a.remove(name), True)[1] if name in a else False
    side = int(opt('--side', '3'))
    steps = int(float(opt('--steps', '20e6')))
    gap = int(float(opt('--gap', '400e3')))
    par = int(opt('--par', '4'))
    out = opt('--out', None)
    keep = flag('--keep') or True
    snap = Path(a[0]).resolve()
    cands = json.load(sys.stdin if a[1] == '-' else open(a[1]))
    out = Path(out).resolve() if out else ROOT / os.environ.get('CMD_WORK', 'scratchpad/cmd1') / 'rollout_out' / snap.stem
    t = time.time()
    res, best = rollout(snap, side, cands, steps, gap, par, out, keep)
    for r in res:
        print(json.dumps(r, separators=(',', ':')))
    print(json.dumps(dict(best=best, name=res[best]['name'], wall_s=round(time.time() - t, 2))))


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
