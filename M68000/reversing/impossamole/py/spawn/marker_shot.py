"""Type-251 marker proof (README "Spawn types", item d): a shot that reaches a marker removes it and releases a fruit.

    ATARI_NOTRACE=1 uv run python marker_shot.py [snap]

Static reading: `$017982` (called per slot 0-5 from the object loop at `$012e0e`) handles kind-0 objects with 79(A0) = 9
(type 251's descriptor +3): `bsr $013bec` is the shot-vs-object test (projectile slots 16-19, `$b71a` contact, carry set
on a hit); on a hit `clr.w 0(A0)` removes the marker and `bsr $01366e` (D1 = D2 = 0) spawns the object type
`$0179d8[(world-1)*4 + random & 3]` at the marker's x,y and sets its 78(A0) = 1 (`$179d0`). World 3's four types are 105-108
(the fruit). A fruit (79 = 8) with 78 = 1 then hops and falls through `$0179ec`/`$017a72` until it lands.

Live (from pass99/warp_up112.snap, three markers in a row at y=152, slots 0, 2, 3): health poked full (labelled), one real
fire pulse per shot (`kbd 80` held one poll cycle) to create a projectile, then the projectile's x,y (slot 16, `$1a9ac`)
is POKED onto the marker (labelled: it stands in for aiming). Control: a shot poked 80 px away from every marker.
`hits` counts `$01799c` (marker removed) and `$01366e` (spawn).
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from replx import Repl

snap = sys.argv[1] if len(sys.argv) > 1 else 'scratchpad/impossamole/pass99/warp_up112.snap'


def slots05(r):
    return [(s, o['x'], o['y'], o['frame'], o['b79'], o['b78']) for s in range(6) for o in [r.obj(s)] if o['tw']]


def shoot(r, x, y):
    r.run('w bb74 12120300', 'kbd ff', 'kbd 80', 's 30000', 'kbd ff', 'kbd 00', 's 4000')
    r.run(f'w 1a9ac {x & 0xffff:04x}{y & 0xffff:04x}')
    return r.run('hits 60000 17994 1799c 1366e')


with Repl(snap) as r:      # control 2: the hero standing on a marker does nothing
    m0 = r.obj(0)
    r.run('w bb74 12120300')
    r.poke(0x1a574, (m0['x'] & 0xffff).to_bytes(2, 'big') + ((m0['y'] - 8) & 0xffff).to_bytes(2, 'big'))
    out = r.run('hits 300000 12e4a 1799c 1366e')
    n = {l.split()[0]: int(l.split()[1]) for l in out}
    print(f"control: hero POKED onto marker slot 0 at ({m0['x']},{m0['y']}), 300000 steps: marker-contact no-op `$012e4a` x{n['$012e4a']}, "
          f"removal `$01799c` x{n['$01799c']}, spawn `$01366e` x{n['$01366e']}; slots 0-5 {slots05(r)}")

with Repl(snap) as r:
    print('start  ', slots05(r))
    out = shoot(r, 200, 20)
    print('control shot at (200,20), hits:', [l.split()[:2] for l in out])
    print('  slots 0-5:', slots05(r))
    for slot in (3, 2, 0):
        m = r.obj(slot)
        assert m['b79'] == 9, ('not a marker', slot)
        for attempt in range(1, 6):   # a shot only registers if a projectile exists when it is poked: retry
            out = shoot(r, m['x'], m['y'])
            n = {l.split()[0]: int(l.split()[1]) for l in out}
            if n['$01799c']:
                break
        r.run('s 400000')
        print(f"shot onto marker slot {slot} at ({m['x']},{m['y']}), attempt {attempt}, hits:", [l.split()[:2] for l in out])
        print('  slots 0-5:', slots05(r))

with Repl(snap) as r:      # real shot, nothing poked but the hero's position (labelled): the shot spawns 20 px in front of the hero
    m2 = r.obj(2)
    r.run('w bb74 12120300')
    r.poke(0x1a574, ((m2['x'] - 22) & 0xffff).to_bytes(2, 'big') + ((m2['y'] - 12) & 0xffff).to_bytes(2, 'big'))
    nmark = lambda: sum(1 for x in slots05(r) if x[4] == 9)
    print(f"natural shots: hero POKED to ({m2['x'] - 22},{m2['y'] - 12}); markers before: {nmark()}")
    for attempt in range(1, 6):
        r.run('kbd ff', 'kbd 80', 's 30000', 'kbd ff', 'kbd 00', 's 60000')
        print(f'  after fire pulse {attempt}: markers {nmark()}, fruit (79 = 8, 78 = 1) {[x for x in slots05(r) if x[4] == 8]}')

# stacked markers (several records at the same column and y, "clusters at one spot"): does one shot release one fruit or all?
# The snapshot is in fire mode `$227fa` = 1 (a pickup's special shot, whose shot has 79(A1) = 1: `$013bec` lets it hit several
# markers in one frame, `cmpi.b #$1,79(A1)`); with `$227fa` POKED to 0 (labelled) the ordinary shot is spent on the first marker.
STACK = 'scratchpad/impossamole/gameplay_explore/pass84_uponly_4_8M.snap'
for mode in (None, 0):
    with Repl(STACK) as r:
        if mode is not None:
            r.poke(0x227fa, bytes([mode]))
            r.poke(0x227fb, b'\0')
        nmark = lambda: sum(1 for x in slots05(r) if x[4] == 9)
        m = r.obj(0)
        print(f"stack, fire mode {r.mem(0x227fa, 1)[0]}: markers {nmark()} at {[(x[1], x[2]) for x in slots05(r) if x[4] == 9]}")
        for k in range(1, 4):
            for attempt in range(1, 6):
                before = nmark()
                shoot(r, m['x'], m['y'])
                if nmark() < before:
                    break
            print(f"  shot {k} (attempt {attempt}): markers {before} -> {nmark()}, shot 79(A1) = {r.obj(16)['b79']}, fruit {len([x for x in slots05(r) if x[4] == 8])}")
