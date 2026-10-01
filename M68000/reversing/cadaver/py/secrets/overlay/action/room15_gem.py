"""room15_gem.py: room 15's ten-visit reveal, by natural input.  Room 15's entry block (`room_scripts_level0.txt`: `VAR 8 += 1`, then `SHOW` of 414, 424-431 for counts 1-9 and of 131 at count 10) is
driven by walking Up into room 15 and Down out of it, starting from room 16 (`ck_e_room16.snap`, variable 8 = 2).  Variable 8 is 2 at room 16 (the route's own first two entries count) and reads `0a` after the eighth
Up (the entry runs a moment after the arrival, hence the `s 150000`); the gem 131 then stands at (8,49,6,46), reached by Up to the stall at y lead 56 and Left to the stall at (14,55,8,49) (a lane of y 49..55 between the roaming hazard 902, whose touch costs 5 health, and the stone
428); the fire probe offers 131 with icons 2 (TAKE), 10, 11, 6, TAKE runs 131's event-0 block (verb 5: XP += 26 and verb 6: GOLD += 100, XP += 100 / 4), and the object is consumed.

    cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/room15_gem.py          (about 4 min)

Expected: variable 8 2 -> 10 over eight Up entries, health 33 throughout, probe (131, [2, 10, 11, 6]), gold 0 -> 100, XP 106 -> 157, rucksack count unchanged.  Walking Up through x 13..20 instead of the lane
costs 30 health (33 -> 3 in one crossing).  Checkpoints: r16/ck_f_var10.snap, ck_f_taken131.snap."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route_lib import *
from route_to_room16 import take


def var8(r): return r.a5(2282 + 8, 1)[0]


def main():
    r = Repl(SN + 'ck_e_room16.snap'); t = Tally(r)
    h0, g0, x0 = r.w(HEALTH), r.l(A5 + 1188), r.l(A5 + 1192)
    print('start: room %d health %d var8 %d gold %d xp %d' % (r.w(ROOM), h0, var8(r), g0, x0), flush=True)
    assert r.w(ROOM) == 16 and var8(r) == 2
    trips = 0
    while var8(r) < 10 and trips < 12:
        hold(r, UP); r.cmd('s 150000'); print('   U  room %d var8 %d health %d' % (r.w(ROOM), var8(r), r.w(HEALTH)), flush=True)
        if var8(r) >= 10: break
        hold(r, DOWN); r.cmd('s 100000'); trips += 1
    assert var8(r) == 10 and r.w(ROOM) == 15
    ck(r, 'f_var10'); r.close()
    r = Repl(SN + 'ck_f_var10.snap'); t = Tally(r); r.cmd('s 50000')
    print('   up', goto(r, UP, lambda p: p[1] <= 56)); print('   left', goto(r, LEFT, lambda p: p[2] <= 8, maxn=200))
    print('at the gem: pos', pos(r), 'health', r.w(HEALTH)); assert pos(r) == (14, 55, 8, 49) and r.w(HEALTH) == h0
    take(r, t, 131)
    print('gold %d -> %d, XP %d -> %d, rucksack count %d, health %d' % (g0, r.l(A5 + 1188), x0, r.l(A5 + 1192), r.a5(2438, 1)[0], r.w(HEALTH)))
    assert (r.l(A5 + 1188), r.l(A5 + 1192)) == (g0 + 100, x0 + 51)
    ck(r, 'f_taken131'); r.close()


def ck(r, name): r.snap(SN + 'ck_%s.snap' % name)


if __name__ == '__main__':
    main()
