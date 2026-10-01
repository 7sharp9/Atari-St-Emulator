"""route_treasury_to_room16.py: natural joystick/keyboard input only, nothing poked or injected.
Room 37 (the treasury, `rwn2/taken53.snap`: crown 53 and skeleton key 104 carried, health 35, XP 132) -> `L` puts LEVER 86 in front (icons 7, 11, 6) -> icon 7 teleports to room 34 (script `37 22 2 2 0`; the
hero lands at (16,16,10,10)) -> `R` room 32 -> `U` room 33 -> `D` 32 -> `R` 31 -> `R` (stall at x 66..72) -> `U` room 30 (44,47,38,41) -> goto left to x lead 34, `U` to the stall at y 9..15
(water 214 in front, a non-obstacle; icon 9 drinks it: 35 -> 37) -> `R` through door `$1d` into room 16 (13,20,7,14), health 37.  Every hold starts from a reopened snapshot (`Repl.__init__` runs `s 1`;
trek's node semantics).  Health 35 on every leg: the legs were found by a breadth-first search over holds pruned on health loss (room 31's floor and room 15 cost 30 elsewhere).

    cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/route_treasury_to_room16.py [run name] [start snap]      (about 2 min; snapshots to r16/t16_<run>/ck_NN_*.snap)

Run twice with two names and compare: the logs and the 12 checkpoints are identical (86th pass, also against the exploring agent's runs).  Its end snapshot `ck_12_R_to_16.snap` is the start of
`route_room16_to_door2a.py`."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_lib import *

K = {'U': UP, 'D': DOWN, 'L': LEFT, 'R': RIGHT}


def main():
    run = sys.argv[1] if len(sys.argv) > 1 else 'run1'
    start = sys.argv[2] if len(sys.argv) > 2 else OUT + 'rwn2/taken53.snap'
    d = SN + 't16_' + run + '/'; os.makedirs(d, exist_ok=True)

    def reopen(r, name):
        path = d + 'ck_%s.snap' % name
        r.snap(path); r.close()
        return Repl(path)

    def leg(r, name, f):
        h0 = r.w(HEALTH); res = f(r)
        print('%-12s room %2d pos %s health %d -> %d%s' % (name, r.w(ROOM), pos(r), h0, r.w(HEALTH), '  ' + str(res) if res is not None else ''), flush=True)
        return reopen(r, name)

    r = Repl(start)
    print('start: room %d pos %s health %d xp %d ruck %s' % (r.w(ROOM), pos(r), r.w(HEALTH), r.l(A5 + 1192), type8(r)['recs'][:type8(r)['count'] + 2]), flush=True)
    assert r.w(ROOM) == 37
    r = leg(r, '01_L_lever', lambda r: hold(r, LEFT))

    def lever(r):
        t = Tally(r); open_panel(r, t); ic = icons(r); pick_icon_id(r, t, 7); r.cmd('s 300000')
        assert ic == [7, 11, 6], ic; assert r.w(ROOM) == 34
        return 'icons %s -> room 34' % ic
    r = leg(r, '02_lever_icon7', lever)
    for i, (mv, want) in enumerate([('R', 32), ('U', 33), ('D', 32), ('R', 31), ('R', 31), ('U', 30)]):
        r = leg(r, '%02d_%s' % (3 + i, mv), lambda r: hold(r, K[mv]))
        assert r.w(ROOM) == want, (mv, r.w(ROOM))
    r = leg(r, '09_goto_L', lambda r: goto(r, LEFT, lambda p: p[0] <= 34))
    r = leg(r, '10_U_stall', lambda r: hold(r, UP))

    def drink(r):                # the probe would cancel the panel, so the drink is a plain panel run from the stall
        t = Tally(r); h0 = r.w(HEALTH); t.reset(); open_panel(r, t); ic = icons(r)
        pick_icon_id(r, t, 9); t.run(100000, sites=[0xa5c0, 0xa5d2, 0xfe24, 0x10cc8])
        assert r.w(HEALTH) == h0 + 2, (h0, r.w(HEALTH)); return 'icons %s, icon 9 hits %s' % (ic, t.show())
    r = leg(r, '11_drink214', drink)
    r = leg(r, '12_R_to_16', lambda r: hold(r, RIGHT))
    assert r.w(ROOM) == 16
    print('arrived: room %d pos %s health %d xp %d' % (r.w(ROOM), pos(r), r.w(HEALTH), r.l(A5 + 1192)))
    print('ruck', type8(r)['recs'][:type8(r)['count'] + 2])
    r.close()


if __name__ == '__main__':
    main()
