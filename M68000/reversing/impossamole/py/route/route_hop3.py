"""Hop 3: walk the hero with real input from room 188..285 (room188.snap) to the block-283 top exit into 299..318.

    uv run python reversing/impossamole/py/route/route_hop3.py [seg ...] [--from <seg>] [--list]

Each segment is a function `segN(d)` driving a `route_driver.Driver`; a segment starts from the previous segment's
end snapshot (`snaps/<seg>.snap`) and writes `segs/<seg>.repl` (replayable), `segs/<seg>.log` and its own end snapshot.
"""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_driver import *

BASE = 'scratchpad/impossamole/agents/hop3'
START = 'scratchpad/impossamole/pass103/room188.snap'
SEGS = []


def seg(fn):
    SEGS.append(fn)
    return fn


def rep(d, why):
    r = d.last
    print(f'  [{why}] {r.brief()}', flush=True)


def walk_to(d, wx, bits=RIGHT, why='walk', **kw):
    """Walk until the hero's left-edge map x reaches `wx` (>= for right, <= for left). Walking is ~1 px per 12-14k
    steps (2 px per game update of ~25k steps), so the budget is 20k steps per pixel."""
    cmp = (lambda s: s.wx >= wx) if bits & RIGHT else (lambda s: s.wx <= wx)
    n = abs(wx - d.last.wx)
    r = d.hold(bits, until=cmp, max_steps=max(60_000, 20_000 * n), why=why, **kw)
    return r


@seg
def seg1_pillar_totem(d):
    """Plank (wx 6080) -> hop up onto the stone pillar (top y=112), hop over the 32 px totem, walk off to the floor."""
    d.poke_health('segment start: health full (chasers bite)')
    d.hold(RIGHT, until=lambda s: s.wx >= 6112, max_steps=400_000, why='walk to pillar wall'); rep(d, 'at pillar')
    d.hop(RIGHT, why='pillar hop'); rep(d, 'on pillar')
    d.hold(RIGHT, until=lambda s: s.wx >= 6154, max_steps=300_000, why='walk to totem'); rep(d, 'at totem')
    d.hop(RIGHT, why='totem hop'); rep(d, 'on totem')
    d.hold(RIGHT, until=lambda s: s.y >= 144 and s.st in (0, 1), max_steps=600_000, why='off the pillar'); rep(d, 'floor')


@seg
def seg2_plateau_edge(d):
    """Floor -> hop up onto the first dirt plateau (cols 804..811, top y=112) and walk to its right edge above the water."""
    d.poke_health('segment start: health full')
    walk_to(d, 6400, why='walk to plateau wall'); rep(d, 'at wall')
    d.hop(RIGHT, why='plateau hop'); rep(d, 'on plateau')
    walk_to(d, 6480, why='to edge'); rep(d, 'at edge')


@seg
def seg3_water1(d):
    """First water pit (wx 6496..6591, 96 px): hop from the plateau edge onto the crocodile in the water (it sits
    under the hero and bites once, 1 hp), walk right on it, it bounces the hero onto the second plateau, walk to its
    right edge and drop to the floor."""
    d.poke_health('segment start: health full')
    walk_to(d, 6488, why='to water edge'); rep(d, 'edge')
    ok, s = d.hop(RIGHT, why='water hop', land_max=1_600_000); rep(d, 'on croc')
    walk_to(d, 6600, why='croc -> plateau 2'); rep(d, 'plateau 2')
    walk_to(d, 6660, why='off plateau 2'); d.land(RIGHT, why='drop to floor'); rep(d, 'floor')


@seg
def seg4_notches(d):
    """Two 8 px deep, 32 px wide dips in the floor (cols 848..851 and 860..863, wx 6784..6815 and 6880..6911). Walking
    into one drops the hero 8 px and the 8 px step on the far side stops it (it stalls there while a ground enemy and
    the chaser bite), so hop each from the edge (take-off wx <= 6775 / 6871)."""
    d.poke_health('segment start: health full')
    walk_to(d, 6768, why='to notch 1'); rep(d, 'notch 1 edge')
    d.hop(RIGHT, why='notch 1 hop'); rep(d, 'after notch 1')
    walk_to(d, 6862, why='to notch 2'); d.land(RIGHT, why='settle'); rep(d, 'notch 2 edge')
    d.hop(RIGHT, why='notch 2 hop'); rep(d, 'after notch 2')
    walk_to(d, 6930, why='past notch 2'); d.land(RIGHT, why='settle'); rep(d, 'floor')


@seg
def seg5_stone_hole(d):
    """Floor -> hop onto stone pillar 1 (cols 884..891, top y=112), hop across the 32 px hole (cols 892..895, the
    block-223 bottom exit: do not fall in) onto pillar 2 (896..903), walk off its right end onto the floor."""
    d.poke_health('segment start: health full')
    walk_to(d, 7044, why='to pillar 1 wall'); rep(d, 'wall')
    d.hop(RIGHT, why='pillar 1 hop'); rep(d, 'on pillar 1')
    walk_to(d, 7120, why='to pillar 1 edge'); rep(d, 'edge')
    d.hop(RIGHT, why='hole hop'); rep(d, 'on pillar 2')
    walk_to(d, 7240, why='off pillar 2'); d.land(RIGHT, why='drop to floor'); rep(d, 'floor')


@seg
def seg6_pits(d):
    """Four water pits (cols 908..915 64 px, 924..939 128 px, 948..951 32 px, 960..975 128 px) separated by dirt mounds
    with a log staircase each. Holding right is enough: each pit has crocodiles at the surface that the hero lands on
    and that bounce it on (each bounce costs 1 hp, the bee costs about 1 hp per 150k steps)."""
    d.poke_health('segment start: health full')
    walk_to(d, 7250, why='to pit 1 edge'); rep(d, 'pit 1 edge')
    for tgt in (7400, 7540, 7700, 7900):
        d.hold(RIGHT, until=lambda s, tgt=tgt: s.wx >= tgt and s.st in (0, 1), max_steps=6_000_000, why=f'pits -> {tgt}'); rep(d, f'wx {tgt}')
    d.land(RIGHT, why='settle'); rep(d, 'floor')


@seg
def seg7_pillars(d):
    """Second pillar pair (pillar 1 cols 992..999, plank 1000..1003, pillar 2 1004..1011; no totems): hop up onto
    pillar 1, hop across the plank gap onto pillar 2, walk off its right end."""
    d.poke_health('segment start: health full')
    walk_to(d, 7908, why='to pillar 1 wall'); rep(d, 'wall')
    d.hop(RIGHT, why='pillar 1 hop'); rep(d, 'on pillar 1')
    walk_to(d, 7982, why='to pillar 1 edge'); rep(d, 'edge')
    d.hop(RIGHT, why='gap hop'); rep(d, 'on pillar 2')
    walk_to(d, 8110, why='off pillar 2'); d.land(RIGHT, why='drop to floor'); rep(d, 'floor')


@seg
def seg8_stairs_roof(d):
    """Log staircase up to the temple (cells (1040,y152)..(1047,y96), one-way steps over the block-261 bottom-exit hole
    at cols 1044..1047 -- walking right along the floor falls into it): two hops up the steps onto the stone roof
    (cols 1048..1059, top y=96), walk right off it, over the step (cols 1060..1067, top y=128), down to the floor."""
    d.poke_health('segment start: health full')
    walk_to(d, 8296, why='to stair foot'); rep(d, 'stair foot')
    d.hop(RIGHT, why='stair hop 1'); rep(d, 'stair step')
    d.hop(RIGHT, why='stair hop 2'); rep(d, 'stair top')
    walk_to(d, 8560, why='over roof and step'); d.land(RIGHT, why='drop to floor'); rep(d, 'floor')


def climb_to(d, y, why='climb', max_steps=1_500_000):
    """Hold up on a ladder until the hero's y <= `y`, then release (holding up past the top starts a jump)."""
    return d.hold(UP, until=lambda s: s.y <= y and s.st != 4 or s.y <= y, max_steps=max_steps, why=why)


@seg
def seg9_ladder_corridor(d):
    """Ladder at cols 1080..1081 (base at the floor) up to the y=64 ledge (hero y=48), then right along the corridor
    on top of the low ceiling slab (cols 1084..1107, over the first three floor totems), drop through the slab gap
    (cols 1108..1111) onto the last totem / floor."""
    d.poke_health('segment start: health full')
    walk_to(d, 8634, why='to ladder'); rep(d, 'ladder foot')
    climb_to(d, 48); rep(d, 'ledge top')
    walk_to(d, 8880, why='along the corridor'); rep(d, 'over the gap')
    d.land(RIGHT, why='drop'); rep(d, 'landed')


@seg
def seg10_bead_ladder(d):
    """Floor under the overhanging wall (cols 1112..1123) to the open shaft area, hop up-left onto the y=128 bead platform
    (cols 1124..1127), align on the ladder (cols 1124..1125) and climb it to the y=64 ledge (hero y=48)."""
    d.poke_health('segment start: health full')
    walk_to(d, 9036, why='to under the shaft'); d.land(RIGHT, why='settle'); rep(d, 'floor right of the bead')
    ok, s = d.hop(LEFT, why='bead hop'); rep(d, 'on bead')
    walk_to(d, 8988, bits=LEFT, why='align to ladder'); rep(d, 'aligned')
    climb_to(d, 48); rep(d, 'ledge')


@seg
def seg11_shaft_exit(d):
    """From the y=64 ledge (cols 1124..1127) hop right across the 32 px gap (1128..1131) onto the y=64 bead platform in
    the block-283 shaft (cols 1132..1135), hop straight up onto the y=32 bead, then jump straight up out of the top
    of the shaft: the block-283 top exit."""
    d.poke_health('segment start: health full')
    walk_to(d, 9012, why='to ledge edge'); rep(d, 'ledge edge')
    ok, s = d.hop(RIGHT, why='gap hop'); rep(d, 'on y64 bead')
    ok, s = d.hop(NONE, why='hop up to y32 bead'); rep(d, 'on y32 bead')
    ok, s = d.hop(NONE, why='jump out of the shaft', land_max=1_600_000); rep(d, 'after exit jump')


def run(names):
    prev = START
    order = [f.__name__ for f in SEGS]
    for f in SEGS:
        n = f.__name__
        endsnap = f'{BASE}/snaps/{n}.snap'
        if names and n not in names:
            if os.path.exists(os.path.join(ROOT, endsnap)):
                prev = endsnap
            continue
        print(f'== {n}: from {prev}', flush=True)
        d = Driver(prev, f'{BASE}/segs/{n}', tick=8000, checkpoint_every=250, ckpt_dir=f'{BASE}/ckpt/{n}')
        f(d)
        d.finish(endsnap)
        print(f'== {n}: done, {d.total_steps} steps, hurts={len(d.hurts)}', flush=True)
        prev = endsnap


if __name__ == '__main__':
    args = sys.argv[1:]
    if '--list' in args:
        print([f.__name__ for f in SEGS]); sys.exit()
    run(args)
