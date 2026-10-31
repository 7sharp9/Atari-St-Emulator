"""The start room and hops 1-2: from a cold-boot start room (room 0..137) to room 188..285 on real input with no poke, as `route_driver.Driver` segments.

    uv run python reversing/impossamole/py/route/route_hop1_2.py [--guard BEST|none] [--start <snap>] [--out <dir>] [seg ...]

Start snapshot: `pass108/start_install.snap`, written by `coldboot_start_room.repl` (cold boot `800000 repl`, boot menu, title, world select, confirm The
Amazon, stop at `$bbd8`, the level install's health write; about 17 s, deterministic) with the hero not yet placed. Each segment starts from the previous one's end snapshot and writes `<out>/<guard>/<seg>.{snap,repl,log}`;
the concatenated `.repl` files replay in one process. `--guard BEST` drives `policy.py`'s `PolicyDriver` (fire at killable enemies, hop immune ones); no
segment pokes. World x `wx` is the hero's left edge in map pixels (col = wx // 8, block = col // 4). `--guard explore` is a plain `Driver` that refills
health at 4 (labelled pokes), for scouting only.

Status: segments 1-3 only, to box 2 at wx 692 (cols 84-91), about 5% of the start room. With weapon 1 they cost 6 hp under
`--set '{"hop": false, "snipe": null, "stand_fire": null}'` (seg1 1: the `$015b3c` flier at wx 326; seg2 2: the monkey `$015934` dropping at wx 422-434;
seg3 3: a snake `$015c82` at wx 550 and two water hits in pit A, whose crocodile reads hp 254) and 8 under plain `BEST`, whose dodge hop at wx 316 lands in
spike pit 2. A start delay of 0 to 112 frames (`hop12_sweep.py`) never does better than 6.
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_driver import *
import pits

pits.PITS.update({'A': (556, 680)})   # start-room water pit cols 72-83 (wx 576-671) between box 1 (top y 128) and box 2 (wx 672), crocodile type 130

BASE = 'scratchpad/impossamole/pass108/route'
START = 'scratchpad/impossamole/pass108/start_install.snap'
SEGS = []
DELAY = 0    # steps idled after the hero is placed (hop12_sweep.py sets it; 0 in the recorded route)


def seg(fn):
    SEGS.append(fn)
    return fn


def rep(d, why):
    print(f'  [{why}] {d.last.brief()} t={d.total_steps}', flush=True)


def walk_to(d, wx, bits=RIGHT, why='walk', **kw):
    cmp = (lambda s: s.wx >= wx) if bits & RIGHT else (lambda s: s.wx <= wx)
    n = abs(wx - d.last.wx)
    return d.hold(bits, until=cmp, max_steps=max(60_000, 20_000 * n), why=why, **kw)


@seg
def seg1_floor(d):
    """Wait for the level to place the hero (x 128, y 144, wx 96), then right along the floor: hop the 8 px notch (cols 24-27, wx 192) and the two spike
    pits (cols 36-39 and 44-47, wx 288 and 352)."""
    d.hold(NONE, until=lambda s: s.x == 128 and s.y == 144, max_steps=3_000_000, why='hero placed'); rep(d, 'placed')
    if DELAY:
        d.hold(NONE, max_steps=DELAY, why='start delay')
    walk_to(d, 180, why='to notch'); rep(d, 'notch edge')
    d.hop(RIGHT, why='notch hop'); rep(d, 'past notch')
    walk_to(d, 278, why='to spike pit 1'); rep(d, 'pit 1 edge')
    d.hop(RIGHT, why='pit 1 hop'); rep(d, 'past pit 1')
    walk_to(d, 342, why='to spike pit 2'); rep(d, 'pit 2 edge')
    d.hop(RIGHT, why='pit 2 hop'); rep(d, 'past pit 2')


@seg
def seg2_box(d):
    """Right along the floor (cols 48-63) under the monkey (type 110, spawn col 53) to the 32 px box (cols 64-71, top y 128), hop onto it."""
    walk_to(d, 500, why='to box'); rep(d, 'box wall')
    d.hop(RIGHT, why='box hop'); rep(d, 'on box')


@seg
def seg3_pit_a(d):
    """Water pit A (cols 72-83): walk to the box's right edge, hop onto the crocodile, ride, hop onto box 2 (pits.cross)."""
    walk_to(d, 556, why='to box edge'); rep(d, 'box edge')
    ok, trace = pits.cross(d, 'A', stop_on_loss=False)
    print('  cross', ok, trace, flush=True); rep(d, 'box 2')


SET = {}     # --set '{"hop": false}': overrides of the guard's policy parameters


def make_driver(guard, snap, name):
    if guard == 'explore':   # exploration only: plain Driver that refills health at 4 (a labelled poke)
        return Driver(snap, name, tick=8000)
    if guard == 'none':
        return Driver(snap, name, tick=8000, hp_floor=-1)
    import policy
    return policy.PolicyDriver(snap, name, tick=8000, P=dict(policy.POLICIES[guard], **SET))


def run(names, guard='BEST', start=START, out=BASE, segs=None):
    prev = start
    for f in (segs or SEGS):
        n = f.__name__
        endsnap = f'{out}/{guard}/{n}.snap'
        if names and n not in names:
            if os.path.exists(os.path.join(ROOT, endsnap)):
                prev = endsnap
            continue
        print(f'== {n}: from {prev}', flush=True)
        d = make_driver(guard, prev, f'{out}/{guard}/{n}')
        hp0 = d.last.hp
        f(d)
        d.finish(endsnap)
        hurts = [(h['wx'], h['hp']) for h in (getattr(d, 'hurt_list', None) or d.hurts)]
        print(f'== {n}: done, {d.total_steps} steps, hp {hp0} -> {d.last.hp}, hurts {hurts}', flush=True)
        prev = endsnap
        if d.last.hp <= 0:
            print('   hero dead, stopping'); break
    return prev


if __name__ == '__main__':
    a = sys.argv[1:]
    guard = a[a.index('--guard') + 1] if '--guard' in a else 'BEST'
    start = a[a.index('--start') + 1] if '--start' in a else START
    out = a[a.index('--out') + 1] if '--out' in a else BASE
    if '--set' in a:
        SET.update(json.loads(a[a.index('--set') + 1]))
    skip = {guard, start, out, a[a.index('--set') + 1] if '--set' in a else None}
    names = [x for x in a if not x.startswith('--') and x not in skip]
    if '--list' in a:
        print([f.__name__ for f in SEGS]); sys.exit()
    run(names, guard, start, out)
