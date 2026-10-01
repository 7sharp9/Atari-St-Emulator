"""route_to_room16.py: natural joystick/keyboard input only (nothing injected or poked).  CAVERN with the pickaxe taken -> room 12 -> the wall of room 12 broken with the thrown
pickaxe -> rooms 13, 14, 19, 61, 68 (large steel key 240) -> 62 (key applied to object 239: doors $23-$26 open) -> 66 (bronze key 155) -> 19, 20 (door $20 opens with key 155)
-> 22 -> 23 (EXAMINE of object 325 shows the skeleton key 104, taken from the top of 325 after a jump) -> back through 22, 20, 19, 14, 13 -> room 15, object 81: the skeleton key
applied through the rucksack panel (icon $c, event 18) clears door $18; Down then leaves room 15 for room 16.

    cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/route_to_room16.py [all|a|b|c|d|e|f]

The whole chain runs in one process (`all`, about 5 minutes); every stage also writes its checkpoint snapshot under scratchpad/cadaver/secrets_out/action/r16/ck_*.snap, and the stage
letters resume from the previous stage's snapshot:
  a  sv_held_lever (pickaxe taken, TUNNEL lever in front) -> lever 144 -> key 73 (room 11) -> east door $3b -> lever 472 (room 8) -> door $22 -> room 12   (ck_a_room12)
  b  room 12: throw the pickaxe twice, walk Down, Left, Down to room 13                                                                                  (ck_b_room13)
  c  room 13 -> 15 -> 13 -> 14 -> 19 -> 61 -> 68, key 240, -> 62 (apply to 239) -> 66, key 155 -> 19 -> 20                                              (ck_c_room20)
  d  room 20 -> 22 -> 23: stall at the south tomb, jump onto 325, drop off its east end, EXAMINE 325, climb again, TAKE 104                                (ck_d_key104)
  e  room 23 -> 22 -> 20 -> 19 -> 14 -> 13 -> 15, apply 104 to object 81 (icon $c), door $18 open, Down -> room 16                                        (ck_e_room16)
Imports trek/drv through route_lib."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route_lib import *
from route_to_room12 import leg, go_x   # the 82nd-pass legs (route_to_room12's main is guarded)
K = {'U': UP, 'D': DOWN, 'L': LEFT, 'R': RIGHT}


_n = [0]
def RL(r, name=None):
    """snapshot, close and reopen (Repl.__init__ runs `s 1`): the explore runs of this route hopped between snapshots, and a hold's outcome depends on that 1-step phase, so the
    script reloads at exactly the same points"""
    _n[0] += 1
    path = SN + 'ck_%s.snap' % (name or 'tmp%d' % _n[0])
    r.snap(path); r.close(); r = Repl(path)
    return r, Tally(r)


def hops(r, moves, label=''):
    """one reload + one full-length hold per move (trek.bfs semantics: each node is a snapshot)"""
    out = None
    for c in moves:
        r, _ = RL(r)
        out = hold(r, K[c]); print('   %s -> room %2d %s health %d' % (c, out[0], out[1], r.w(HEALTH)), flush=True)
    print('%-44s room %2d pos %s health %d' % (label, r.w(ROOM), pos(r), r.w(HEALTH)), flush=True)
    return r


def ck(r, name): r.snap(SN + 'ck_%s.snap' % name)
def seen(r, label): dump(r, label); classes(r)
def rucksack(r): n = r.a5(2438, 1)[0]; return type8(r)['recs'][:n]


def take(r, t, want, icon=2):
    res = probe(r); print('   probe', res and (res[0], res[1]), flush=True)
    assert res and res[0] == want and icon in res[1], res
    open_panel(r, t); pick_icon_id(r, t, icon)
    print('   rucksack', rucksack(r), flush=True)


def apply_held(r, t, wait):
    """Space opens the rucksack panel of the held item; with an object of class $b in front its list starts with icon $c; fire confirms (event 18)"""
    ruck_panel(r, t, 'space')
    print('   panel icons', icons(r), 'front id %d class %d' % (r.w(A5 + 2128), r.b(A5 + 2476)), 'cursor', cur_icon(r), flush=True)
    pick_icon_id(r, t, 0xc); t.run(wait)


def aim_throw(r, t):
    """select the held pickaxe (Space -> icon $d SELECT), a 35,000-step tap turns the hero Down"""
    print('   selected item', select_held(r, t), flush=True)
    aim(r, DOWN)


def fire_throw(r):
    """fire held 60,000 steps with nothing in front throws the selected item (class byte 2463 = 0 -> $00a19e)"""
    joy(r, FIRE); r.cmd('s 60000'); joy(r, 0)


def stage_a():
    r = Repl(OUT + 'sv_held_lever.snap'); t = Tally(r)
    print('start room', r.w(ROOM), 'pos', pos(r), 'rucksack', rucksack(r))
    res = probe(r); assert res and res[0] == 144 and 7 in res[1]
    open_panel(r, t); pick_icon_id(r, t, 7); t.run(600000)
    leg(r, 'TUNNEL -> 2 -> 6 -> 6 -> 7', [UP, RIGHT, RIGHT, DOWN], 7)
    leg(r, 'room 7 east door $39 -> 10', [go_x(DOWN, lambda p: p[1] >= 19), RIGHT], 10)
    leg(r, 'room 10 -> 11 (door $1a)', [UP, RIGHT, DOWN, RIGHT], 11)
    leg(r, 'room 11 stall at the iron key', [go_x(DOWN, lambda p: p[1] >= 34), RIGHT], 11)
    take(r, t, 73)
    leg(r, 'room 11 -> 10', [LEFT, DOWN, RIGHT, UP, LEFT], 10)
    leg(r, 'room 10 -> 7', [DOWN, LEFT, UP, LEFT], 7)
    leg(r, 'room 7 -> 6', [UP, UP, LEFT, DOWN, RIGHT, UP], 6)
    leg(r, 'room 6 -> 2', [LEFT, LEFT], 2)
    leg(r, 'room 2 -> TUNNEL (door $33)', [DOWN, go_x(LEFT, lambda p: p[0] <= 51), DOWN], 1)
    leg(r, 'TUNNEL -> CAVERN', [DOWN], 0)
    leg(r, 'CAVERN to the east door $3b', [go_x(DOWN, lambda p: p[1] >= 18)], 0)
    leg(r, 'east door with key 73 -> room 8', [RIGHT], 8)
    leg(r, 'room 8 stall at lever 472', [UP], 8)
    d0 = door(r, 0x22)
    open_panel(r, t); pick_icon_id(r, t, 7); t.run(600000)
    print('door $22', d0, '->', door(r, 0x22))
    leg(r, 'room 8 -> CAVERN', [DOWN, LEFT], 0)
    leg(r, 'CAVERN -> TUNNEL -> 2', [UP, UP, UP], 2)
    leg(r, 'room 2 -> 6 -> 7', [RIGHT, RIGHT, DOWN], 7)
    leg(r, 'room 7 south wall to door $22', [DOWN, DOWN, go_x(RIGHT, lambda p: p[0] >= 66), DOWN], 12)
    print('rucksack', rucksack(r)); ck(r, 'a_room12')
    return r, t


def stage_b(r=None, t=None):
    r, t = RL(r) if r is not None else (Repl(SN + 'ck_a_room12.snap'), None)
    t = Tally(r)
    r.cmd('s 100000')
    seen(r, 'room 12 (the wall: 170-177, four z levels of two blocks)')
    print('wall before:', wall(r))
    aim_throw(r, t)
    r, t = RL(r)
    fire_throw(r)
    for _ in range(16): r.cmd('s 100000')
    print('after throw 1:', wall(r))
    r, t = RL(r, 'b_throw1')
    room, p = hold(r, DOWN); print('D (stall in front of the lying pickaxe)', room, p)
    take(r, t, 168); r.cmd('s 100000')
    print('   selected item', select_held(r, t))
    p = goto(r, UP, lambda p: p[1] <= 14); print('back up', p)
    aim(r, DOWN); fire_throw(r)
    for _ in range(14): r.cmd('s 100000')
    print('after throw 2:', wall(r))
    r, t = RL(r, 'b_throw2')
    for mv in 'DDLD':
        room, p = hold(r, K[mv]); print('  ', mv, room, p)
        if room == 13: break
    assert r.w(ROOM) == 13
    r, t = RL(r)
    r.cmd('s 100000'); seen(r, 'room 13'); ck(r, 'b_room13')
    return r, t


def stage_c(r=None, t=None):
    if r is None: r = Repl(SN + 'ck_b_room13.snap')
    r = hops(r, 'DUR', 'room 13 -> 15 -> 13 -> 14')
    r = hops(r, 'RR', 'room 14 -> 19')
    r = hops(r, 'RLRU', 'room 19 -> 61 (door $45)'); assert r.w(ROOM) == 61
    r, t = RL(r)
    r.cmd('s 100000')
    p = goto(r, UP, lambda p: p[1] <= 47); print('   room 61 up to the door $27 row', p)
    room, p = hold(r, LEFT); print('   L ->', room, p); assert room == 68
    r.cmd('s 100000'); seen(r, 'room 68'); r, t = RL(r)
    r.cmd('s 100000')
    goto(r, DOWN, lambda p: p[1] >= 29); room, p = hold(r, LEFT); print('   room 68 stall', room, p)
    take(r, t, 240); ck(r, 'c_key240')
    r = hops(r, 'URU', 'room 68 -> 61 -> 62'); seen(r, 'room 62')
    r = hops(r, 'UUL', 'room 62 stall at object 239')
    r, t = RL(r); r.cmd('s 100000'); w0 = {d: door(r, d) for d in (0x23, 0x24, 0x25, 0x26)}
    apply_held(r, t, 600000)
    print('   hits', t.show())
    print('   doors $23-$26 id words', {hex(d): (w0[d][4:8], door(r, d)[4:8]) for d in w0}, 'rucksack', rucksack(r))
    r, t = RL(r, 'c_applied239'); r.cmd('s 100000')
    goto(r, DOWN, lambda p: p[1] >= 24); goto(r, RIGHT, lambda p: p[0] >= 70, maxn=800); goto(r, DOWN, lambda p: p[1] >= 44)
    room, p = hold(r, RIGHT); print('   R ->', room, p); assert room == 66
    r.cmd('s 100000'); seen(r, 'room 66')
    r = hops(r, 'UR', 'room 66 stall at key 155')
    r, t = RL(r); r.cmd('s 100000'); take(r, t, 155); print('   door $20', door(r, 0x20)); ck(r, 'c_key155')
    r = hops(r, 'LUDLDD', 'room 66 -> 62 -> 61 -> 19')
    r = hops(r, 'R', 'room 19 -> 20 (door $20, key 155)')
    print('   door $20', door(r, 0x20), 'rucksack', rucksack(r)); ck(r, 'c_room20')
    return r, t


def stage_d(r=None, t=None):
    if r is None: r = Repl(SN + 'ck_c_room20.snap')
    r = hops(r, 'URRR', 'room 20 -> 22 -> 23')
    seen(r, 'room 23 at arrival (three tombs; 3 and 4 are 18 high, 325 and 188 lie on 3)')
    r, t = RL(r)
    for c in 'URULDR': hold(r, K[c])
    print('room 23 stall at the south tomb (object 3):', pos(r), 'room', r.w(ROOM))
    assert pos(r) == (23, 74, 17, 68), pos(r)
    r, t = RL(r, 'd_stall')
    # jump: back off 60,000 steps, fire+right; the arc starts ~55,000 steps later; the hero lands on 325 (z base 26) and walks east along its top
    joy(r, LEFT); r.cmd('s 60000'); joy(r, 0); r.cmd('s 30000')
    joy(r, FIRE | RIGHT); r.cmd('s 300000'); joy(r, RIGHT)
    for _ in range(40):
        r.cmd('s 10000')
        if pos(r)[0] >= 44: break
    print('   on top of 325', pos(r), 'z', tuple(r.mem(0x3833c, 2)))
    for _ in range(30):
        r.cmd('s 3000'); p = pos(r); z = tuple(r.mem(0x3833c, 2))
        if p[0] >= 49 or z[1] < 20: break
    joy(r, 0); r.cmd('s 30000'); print('   east end', pos(r), 'z', tuple(r.mem(0x3833c, 2)))
    r, t = RL(r)
    joy(r, RIGHT)
    for _ in range(60):
        r.cmd('s 2000'); z = tuple(r.mem(0x3833c, 2))
        if z[1] != 26: break
    joy(r, 0); r.cmd('s 20000'); print('   dropped onto 188', pos(r), 'z', tuple(r.mem(0x3833c, 2)))
    r, t = RL(r)
    r.cmd('s 100000'); aim(r, LEFT, 50000)
    print('   facing 325 at', pos(r), 'z', tuple(r.mem(0x3833c, 2)), 'facing', r.a5(2273, 1).hex())
    res = probe(r); print('   probe', res and (res[0], res[1])); assert res and res[0] == 325 and 11 in res[1]
    open_panel(r, t); pick_icon_id(r, t, 11); t.run(400000)      # EXAMINE (event 16): the block `SHOW object #104`
    print('   hits', t.show()); print('   104 now in the room:', [e for e in wall(r).split() if e.startswith('104:')])
    r, t = RL(r, 'd_examined')
    # down to the floor, west along the south wall, back to the tomb's west face, jump again, walk east on top: 325's top pushes the key along in front of the hero
    r.cmd('s 60000')
    goto(r, DOWN, lambda p: p[1] >= 79); r.cmd('s 100000')
    room, p = hold(r, LEFT); print('   L', room, p)
    print('   up', goto(r, UP, lambda p: p[1] <= 74))
    room, p = hold(r, RIGHT); print('   R stall', room, p)
    joy(r, LEFT); r.cmd('s 60000'); joy(r, 0); r.cmd('s 30000')
    joy(r, FIRE | RIGHT); r.cmd('s 300000'); joy(r, RIGHT)
    for _ in range(40):
        r.cmd('s 10000')
        if pos(r)[0] >= 41: break
    print('   on top again', pos(r), 'z', tuple(r.mem(0x3833c, 2)), 'facing', r.a5(2273, 1).hex())
    r, t = RL(r)
    r.cmd('s 20000'); take(r, t, 104)
    print('   health', r.w(HEALTH)); ck(r, 'd_key104')
    return r, t


def stage_e(r=None, t=None):
    if r is None: r = Repl(SN + 'ck_d_key104.snap')
    r, t = RL(r)
    for mv in 'RDL': hold(r, K[mv])
    print('   up', goto(r, UP, lambda p: p[3] <= 46))
    room, p = hold(r, LEFT); print('   L ->', room, p); assert room == 22
    r, t = RL(r)
    for mv in 'LLLLLLD': room, p = hold(r, K[mv]); print('   ', mv, room, p)
    assert r.w(ROOM) == 18
    r, t = RL(r)
    for mv in 'ULLLD': room, p = hold(r, K[mv]); print('   ', mv, room, p)
    assert r.w(ROOM) == 15
    r, t = RL(r, 'e_room15')
    r.cmd('s 100000')
    for mv in 'DL': room, p = hold(r, K[mv]); print('   ', mv, room, p)
    print('room 15 stall at object 81:', pos(r), 'health', r.w(HEALTH)); ck(r, 'e_at81')
    res = probe(r); print('   probe', res and (res[0], res[1]), 'health', r.w(HEALTH))
    w0 = door(r, 0x18); print('   door $18', w0)
    ruck_panel(r, t, 'space')
    print('   panel icons', icons(r), 'front id %d class %d' % (r.w(A5 + 2128), r.b(A5 + 2476)), 'cursor', cur_icon(r))
    t.reset(); pick_icon_id(r, t, 0xc); t.run(150000, sites=[0xa682, 0xa6f4, 0xfe24, 0xfe5a, 0x104e2, 0x10514])
    print('   hits', t.show())
    print('   door $18', w0, '->', door(r, 0x18), 'rucksack', rucksack(r), 'health', r.w(HEALTH)); ck(r, 'e_applied')
    room, p = hold(r, DOWN); print('   D ->', room, p)
    assert r.w(ROOM) == 16
    r.cmd('s 100000'); seen(r, 'room 16'); ck(r, 'e_room16')
    return r, t


STAGES = {'a': stage_a, 'b': stage_b, 'c': stage_c, 'd': stage_d, 'e': stage_e}

if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'all'
    r = t = None
    for s in 'abcde':
        if what == 'all' or what == s:
            r, t = STAGES[s](r, t) if (what == 'all' and r is not None) else STAGES[s]()
    if r: r.close()
