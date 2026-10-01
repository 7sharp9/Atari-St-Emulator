"""route_to_room12.py: CAVERN's region to room 12 with natural joystick input only (nothing injected or poked), from `lever_after.snap`
(`lever_operate.py`: TUNNEL, door `$33` open).

The 11 door-id words that are not 0 gate the world.  `$ffff` doors are opened by a script (lever, item applied, touch); a positive id word is an ITEM ID: the
crossing proceeds when `$011256` finds that id in the type-8 list (the rucksack), and `$0071b8` clears the word afterwards when the descriptor's flag byte is 2
(the key is consumed, the door stays open).  So:

  1. TUNNEL -> room 2 -> 6 -> 7 -> 10 -> 11 (doors `$33` open, `$34`, `$44`, `$39`, `$1a`)
  2. room 11: object 73, "A SIMPLE IRON KEY", is the item id of CAVERN's east door `$3b` (descriptor word 73): walk to its stall, probe (73, icons 2 10 11 6), TAKE
  3. back through 10, 7, 6, 2, TUNNEL to CAVERN; at x lead 79, y 13..19 the east door now opens into room 8 (word 73 -> 0, rucksack 1 -> 0)
  4. room 8 holds LEVER 472 (z 16..33): one step short of it (Up from the arrival) the probe returns (472, icons 7 11 6); icon 7 runs its event-5 block
     (`05 05 | 0a 22 | 17`: verb 5 XP += 26, verb 10 CLEAR FLAG `$22`): door `$22` (room 7 south edge, local x about 64) word `$ffff` -> 0, XP 40 -> 66
  5. back to room 7 and Down at x lead 66-67 along the south wall: room 12

    python reversing/cadaver/py/secrets/overlay/action/route_to_room12.py [snap]      # snapshots are written under scratchpad/cadaver/secrets_out/action/r12/"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from trek import *
R12 = OUT + 'r12/'
os.makedirs(R12, exist_ok=True)


def goto(r, bits, cond, chunk=5000, maxn=400):
    """hold `bits` in 5,000-step chunks until `cond(bbox)`; the finer chunk puts the hero on an exact cell (one cell per ~10,000 steps)"""
    joy(r, bits)
    for _ in range(maxn):
        r.cmd('s %d' % chunk)
        if cond(pos(r)): break
    joy(r, 0); r.cmd('s 30000')
    return pos(r)


def leg(r, label, moves, want_room):
    for m in moves:
        room, p = hold(r, m) if isinstance(m, int) else m(r)
    assert r.w(ROOM) == want_room, (label, r.w(ROOM), want_room)
    print('%-34s room %2d pos %s health %d' % (label, r.w(ROOM), pos(r), r.w(HEALTH)), flush=True)


def go_x(bits, test):
    return lambda r: (r.w(ROOM), goto(r, bits, test))


if __name__ == '__main__':
    r = Repl(sys.argv[1] if len(sys.argv) > 1 else OUT + 'lever_after.snap'); t = Tally(r)
    leg(r, 'TUNNEL -> 2 -> 6 -> 6 -> 7', [UP, RIGHT, RIGHT, DOWN], 7)
    leg(r, 'room 7 east door $39 -> 10', [go_x(DOWN, lambda p: p[1] >= 19), RIGHT], 10)
    leg(r, 'room 10 -> 11 (door $1a)', [UP, RIGHT, DOWN, RIGHT], 11)
    leg(r, 'room 11 stall at the iron key', [go_x(DOWN, lambda p: p[1] >= 34), RIGHT], 11)
    res = probe(r); print('probe', (res[0], res[1]) if res else None)
    assert res and res[0] == 73 and 2 in res[1]
    open_panel(r, t); pick_icon_id(r, t, 2)
    n = r.a5(2438, 1)[0]; recs = type8(r)['recs'][:n]; print('rucksack', n, recs); assert recs[0][0] == 73
    r.snap(R12 + 'key73.snap')
    leg(r, 'room 11 -> 10', [LEFT, DOWN, RIGHT, UP, LEFT], 10)
    leg(r, 'room 10 -> 7', [DOWN, LEFT, UP, LEFT], 7)
    leg(r, 'room 7 -> 6', [UP, UP, LEFT, DOWN, RIGHT, UP], 6)
    leg(r, 'room 6 -> 2', [LEFT, LEFT], 2)
    leg(r, 'room 2 -> TUNNEL (door $33)', [DOWN, go_x(LEFT, lambda p: p[0] <= 51), DOWN], 1)
    leg(r, 'TUNNEL -> CAVERN', [DOWN], 0)
    w0 = r.mem(0x6d532, 8).hex()
    leg(r, 'CAVERN to the east door $3b', [go_x(DOWN, lambda p: p[1] >= 18)], 0)
    leg(r, 'east door with key 73 -> room 8', [RIGHT], 8)
    print('door $3b word', w0[4:8], '->', r.mem(0x6d532, 8).hex()[4:8], 'rucksack', r.a5(2438, 1)[0])
    leg(r, 'room 8 stall at lever 472', [UP], 8)
    r.snap(R12 + 'lever472_before.snap')
    d0, xp0 = r.mem(0x6d46a, 8).hex(), r.l(A5 + 1192)
    open_panel(r, t); ic = icons(r); print('icons', ic)
    pick_icon_id(r, t, 7); t.run(600000)
    print('door $22', d0, '->', r.mem(0x6d46a, 8).hex(), 'XP', xp0, '->', r.l(A5 + 1192), 'hits',
          {hex(k): v for k, v in sorted(t.tot.items()) if v and k in (0xa448, 0xa486, 0xfe24)})
    r.snap(R12 + 'lever472_after.snap')
    leg(r, 'room 8 -> CAVERN', [DOWN, LEFT], 0)
    leg(r, 'CAVERN -> TUNNEL -> 2', [UP, UP, UP], 2)
    leg(r, 'room 2 -> 6 -> 7', [RIGHT, RIGHT, DOWN], 7)
    leg(r, 'room 7 south wall to door $22', [DOWN, DOWN, go_x(RIGHT, lambda p: p[0] >= 66), DOWN], 12)
    r.snap(R12 + 'room12.snap'); r.close()
