"""Hop 4: room 299..318 to the boss room 318..326 on real input with no health poke, as `route_driver.Driver` segments (ported from `shop/route_driver.py`).

    uv run python reversing/impossamole/py/route/route_hop4.py [--guard none|BEST] [--start <snap>] [--out <dir>] [--shop] [seg ...]

Without `--shop`: seg1-seg5 from the unpoked end of hop 3 (`agents/unpoked/s11/seg11_shaft_exit.snap`, health 11, weapon 3, coins 100) to the boss room
with health 9. With `--shop`: seg1-seg4, then the mole shop branch (seg6-seg10: walk into the block-313 shaft, wait for the mole, enter, buy the worm can
with the natural coins, leave), then seg5 from the shop's return room: boss room with health 16. Snapshots, `.repl` and `.log` per segment go to
`<out>/<guard>/` (`<out>/<guard>/shop/` for the shop branch); the concatenated `.repl` files replay in one process byte-identically. `--guard BEST` runs
`policy.py`'s `PolicyDriver` (two dodge hops in seg3 over the immune object with handler `$013cb2`, same health at the boss room), `none` the plain `Driver` with `hp_floor=-1` (no refill). No segment calls
`poke_health`. World positions: ladder A at wx 9728, ladder B at 9784, the tunnel end wall at 9896, the 32 px ledge and second wall at 9954, the stair foot at
10078, the pit at block 317 (wx 10128).
"""
import os, sys, json
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_driver import *

BASE = 'scratchpad/impossamole/agents/unpoked/hop4'
START = 'scratchpad/impossamole/agents/unpoked/s11/seg11_shaft_exit.snap'
SEGS = []


def seg(fn):
    SEGS.append(fn)
    return fn


def rep(d, why):
    print(f'  [{why}] {d.last.brief()}', flush=True)


def walk_to(d, wx, bits=RIGHT, why='walk', **kw):
    cmp = (lambda s: s.wx >= wx) if bits & RIGHT else (lambda s: s.wx <= wx)
    n = abs(wx - d.last.wx)
    return d.hold(bits, until=cmp, max_steps=max(60_000, 20_000 * n), why=why, **kw)


def latch(d, bits, n, why='latch'):
    """Hold `bits` for exactly n steps without reading (a fixed wait for the game's own poll), then leave them latched."""
    d.set_bits(bits)
    d.step(n)


@seg
def seg1_ladder_a(d):
    """Walk right along the low tunnel to ladder A (wx 9728), climb it, release up at the top (y=48, state 0)."""
    latch(d, RIGHT, 30_000)
    d.last = d.read_stable()
    walk_to(d, 9720, why='to ladder A'); rep(d, 'ladder A foot')
    d.set_bits(0); d.step(30_000)
    d.hold(UP, until=lambda s: s.st == 0 and s.y < 100, max_steps=3_200_000, why='climb A'); rep(d, 'ladder A top')
    d.step(60_000)


@seg
def seg2_traverse_b(d):
    """Right along the ledge above the rock (row 64) to wx 9784, then down ladder B to the tunnel floor."""
    latch(d, RIGHT, 30_000)
    d.last = d.read_stable()
    walk_to(d, 9784, why='along the ledge'); rep(d, 'ladder B top')
    d.set_bits(0); d.step(30_000)
    d.hold(DOWN, until=lambda s: s.st == 0 and s.y > 120, max_steps=3_000_000, why='down B'); rep(d, 'tunnel floor')
    d.step(30_000)


@seg
def seg3_tunnel_hop(d):
    """Right along the tunnel to its end wall (wx 9896), hop up onto the 32 px ledge (y=112), right to the next wall."""
    latch(d, RIGHT, 30_000)
    d.last = d.read_stable()
    walk_to(d, 9896, why='to tunnel wall'); rep(d, 'tunnel wall')
    d.set_bits(0); d.step(60_000)
    latch(d, UP | RIGHT, 30_000)
    latch(d, RIGHT, 30_000)
    d.hold(RIGHT, until=lambda s: s.st == 0 and s.y == 112, max_steps=1_200_000, why='onto ledge', release=False); rep(d, 'on ledge')
    latch(d, RIGHT, 60_000)
    d.set_bits(0); d.step(30_000)
    d.last = d.read_stable()


@seg
def seg4_wall_hop(d):
    """Hop up the second 32 px step onto the rock top (y=80)."""
    latch(d, UP | RIGHT, 30_000)
    latch(d, RIGHT, 30_000)
    d.hold(RIGHT, until=lambda s: s.st in (0, 1) and s.y == 80, max_steps=1_200_000, why='onto rock top', release=False); rep(d, 'rock top')


@seg
def seg5_pit_exit(d):
    """Right down the stairs and along the grass to the pit at block 317, release right once falling, and wait for the exit checker
    ($df4a) to install room 318..326 (the fade takes several hundred thousand steps), then let the fall settle."""
    latch(d, RIGHT, 30_000)
    d.last = d.read_stable()
    d.hold(RIGHT, until=lambda s: s.st == 3 and s.y > 150 and s.wx >= 10128, max_steps=6_000_000, why='to the pit', release=False); rep(d, 'falling in')
    d.set_bits(0)
    d.hold(NONE, until=lambda s: s.blk == 0x13e, max_steps=1_800_000, why='room install'); rep(d, 'boss room')
    d.step(600_000)
    d.hold(NONE, until=lambda s: s.st == 0 and s.y == 144, max_steps=5_000_000, why='settle'); rep(d, 'landed')
    d.step(100_000)


# ---- the shop branch: from the end of seg4 (rock top) to the worm can and back to the pit (README "The shop"; segments ported from shop/route_driver.py)
def mole_slot(d):
    """The object slot whose per-frame handler is $00e842 (the mole), or None."""
    for o in d.objects():
        if o['type'] and int.from_bytes(o['raw'][86:90], 'big') == 0xe842:
            return o
    return None


def anim_done(d, o):
    """True when the animation list word at anim+idx is $fffd (hold the last frame)."""
    anim = int.from_bytes(o['raw'][22:26], 'big'); idx = int.from_bytes(o['raw'][26:28], 'big')
    return int.from_bytes(d.mem(anim + idx, 2), 'big') == 0xfffd


def shop_bubble(d):
    """(mole frame, bubble frame) of slots 7 and 8 inside the shop."""
    return (int.from_bytes(d.mem(0x1a5de + 6, 2), 'big'), int.from_bytes(d.mem(0x1a64a + 6, 2), 'big'))


def fire_pulse(d, hold=45_000):
    """One real fire press: level 80 held for more than one poll, then released."""
    d.set_bits(FIRE); d.step(hold); d.set_bits(0)


SHOP = []


def shop_seg(fn):
    SHOP.append(fn)
    return fn


@shop_seg
def seg6_shop_walk(d):
    """Down the stairs to the camera limit (wx 10078), then left off the ground into the block-313 shaft where the mole (type 9) sits."""
    latch(d, RIGHT, 30_000)
    d.last = d.read_stable()
    walk_to(d, 10078, why='to the stair foot'); rep(d, 'stair foot')
    d.set_bits(0); d.step(60_000)
    d.hold(LEFT, until=lambda s: s.st == 0 and s.y >= 160, max_steps=3_000_000, why='into the mole shaft'); rep(d, 'in the shaft')
    d.step(30_000)


@shop_seg
def seg7_shop_wait(d):
    """Idle beside the mole until its climb-out animation reaches the hold word $fffd."""
    for _ in range(200):
        o = mole_slot(d)
        if o and anim_done(d, o):
            break
        d.step(50_000)
    else:
        raise RuntimeError('mole animation never finished')
    d.last = d.read_stable(); rep(d, 'mole out')


@shop_seg
def seg8_shop_enter(d):
    """Hold DOWN on the fully emerged mole: the room installer runs with the $ea92 record (blocks 410..418); release once installed and let the fade end."""
    d.hold(DOWN, until=lambda s: s.blk == 0x19a, max_steps=3_000_000, why='enter the shop'); rep(d, 'in the shop')
    d.step(600_000)


@shop_seg
def seg9_shop_buy(d):
    """Walk left onto the worm can (slot 3, item 1, price 75; natural coins 100), fire once, wait for THANK YOU and the health effect."""
    d.hold(LEFT, until=lambda s: shop_bubble(d)[1] not in (0x3e, 0), max_steps=1_500_000, why='onto the worm can', tick=15_000); rep(d, 'on the can')
    d.step(60_000)
    b0 = d.mem(0xbb72, 4)
    fire_pulse(d)
    d.step(600_000)
    b1 = d.mem(0xbb72, 4)
    print(f'  weapon/coins/hp/max before {b0.hex()} after {b1.hex()}  bubble {[hex(v) for v in shop_bubble(d)]}', flush=True)
    d.last = d.read_stable()


@shop_seg
def seg10_shop_exit(d):
    """Walk right to the shopkeeper until the EXIT? bubble ($4d), fire, and wait for the return room (blocks 308..318, hero at wx 10080)."""
    d.hold(RIGHT, until=lambda s: shop_bubble(d)[1] == 0x4d, max_steps=1_500_000, why='to the keeper', tick=15_000); rep(d, 'at the keeper')
    d.step(30_000)
    fire_pulse(d)
    d.hold(NONE, until=lambda s: s.blk == 0x134, max_steps=3_000_000, why='return room'); rep(d, 'back outside')
    d.step(600_000)
    d.last = d.read_stable(); rep(d, 'settled')


def make_driver(guard, snap, name):
    if guard == 'none':
        return Driver(snap, name, tick=8000, hp_floor=-1)
    import policy
    return policy.PolicyDriver(snap, name, tick=8000, P=policy.POLICIES[guard])


def run(names, guard='none', start=START, out=BASE, segs=None, sub=''):
    prev = start
    for f in (segs or SEGS):
        n = f.__name__
        endsnap = f'{out}/{guard}{sub}/{n}.snap'
        if names and n not in names:
            if os.path.exists(os.path.join(ROOT, endsnap)):
                prev = endsnap
            continue
        print(f'== {n}: from {prev}', flush=True)
        d = make_driver(guard, prev, f'{out}/{guard}{sub}/{n}')
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
    guard = a[a.index('--guard') + 1] if '--guard' in a else 'none'
    start = a[a.index('--start') + 1] if '--start' in a else START
    out = a[a.index('--out') + 1] if '--out' in a else BASE
    skip = {guard, start, out}
    names = [x for x in a if not x.startswith('--') and x not in skip]
    if '--list' in a:
        print([f.__name__ for f in SEGS + SHOP]); sys.exit()
    if '--shop' in a:
        # seg1-4, then the shop branch (seg6-10), then seg5 (pit exit) from the shop's return room: the route with the worm can bought
        p = run(names, guard, start, out, SEGS[:4])
        p = run(names, guard, p, out, SHOP, sub='/shop')
        run(names, guard, p, out, SEGS[4:], sub='/shop')
    else:
        run(names, guard, start, out)
