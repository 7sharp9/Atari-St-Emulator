"""route_room23_to_item455.py: natural joystick/keyboard input only, nothing poked.  Room 23 -> 24 (R R U L, goto R to x trail 8, U), `U R` to the stall in front of item 455, TAKE it (icon 2),
`L` to object 454 (class $b, west wall), apply 455 with Space + icon $c: doors $3f (23-26) and $40 (23-25) go from word ffff to 0000 and 455 is consumed; three #447 spiders appear.
Then `D` (room 24 -> 23 at (20,13,14,7), before a spider reaches the hero), door $3f: goto L to x lead 15, `D`, `L`, `D` into room 26 (20,13,14,7), `U` back, door $40: goto U to y lead 59, `R` into room 25 (13,28,7,22).

    cd M68000 && .venv/bin/python <this file> OUTDIR [START SNAP]       (default start: scratchpad/cadaver/secrets_out/action/r16/ck_d_key104.snap, room 23, health 53)

OUTDIR gets the checkpoint snapshots (ck_NN_*.snap) and nothing else is written.  Every hold starts from a reopened snapshot (`Repl.__init__` runs `s 1`; trek's node semantics)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_chain import *


def to_room24(R):
    sc = R.settle_on_change
    for mv in 'RRUL': sc(mv, lambda r, mv=mv: hold(r, K[mv]))
    sc('goto_R8', lambda r: goto(r, RIGHT, lambda p: p[2] >= 8))
    sc('U', lambda r: hold(r, UP), 24)


def item455(R):
    sc = R.settle_on_change
    sc('U', lambda r: hold(r, UP))
    sc('R_stall455', lambda r: hold(r, RIGHT))

    def take(r):
        res = probe(r); assert res and res[0] == 455, res
        t = Tally(r); open_panel(r, t); ic = icons(r); pick_icon_id(r, t, 2); t.run(100000)
        return 'probe %s icons %s ruck count %d recs %s' % (res[:2], ic, type8(r)['count'], type8(r)['recs'][:type8(r)['count'] + 1])
    R.leg('take455', take)
    sc('L_to454', lambda r: hold(r, LEFT))

    def apply(r):
        res = probe(r); assert res and res[0] == 454, res
        t = Tally(r); h0 = r.w(HEALTH)
        ruck_panel(r, t, 'space'); ic = icons(r); pick_icon_id(r, t, 0xc); t.run(150000, sites=[0xa682, 0xa6f4, 0xfe24, 0xfe5a])
        d3f, d40 = door(r, 0x3f), door(r, 0x40)
        assert d3f[4:8] == '0000' and d40[4:8] == '0000', (d3f, d40)
        return 'probe %s icons %s hits %s doors $3f %s $40 %s ruck count %d' % (res[:2], ic, t.show(), d3f, d40, type8(r)['count'])
    R.leg('apply455_on454', apply)


def cross(R):
    """room 24 -> D (room 23 at (20,13,14,7), no spider touched) -> door $3f into room 26 (x 6..12 lane) and back -> door $40 into room 25"""
    sc = R.settle_on_change
    sc('D', lambda r: hold(r, DOWN), 23)
    sc('goto_L15', lambda r: goto(r, LEFT, lambda p: p[0] <= 15))
    sc('D', lambda r: hold(r, DOWN))
    sc('L', lambda r: hold(r, LEFT))
    sc('D_door3f', lambda r: hold(r, DOWN), 26)
    sc('U_back', lambda r: hold(r, UP), 23)
    sc('goto_U59', lambda r: goto(r, UP, lambda p: p[1] <= 59))
    sc('R_door40', lambda r: hold(r, RIGHT), 25)


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    out = a[0]; start = a[1] if len(a) > 1 else OUT + 'r16/ck_d_key104.snap'
    R = Route(out, start)
    print('start: room %d pos %s health %d xp %d ruck count %d doors $3f %s $40 %s' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), type8(R.r)['count'], door(R.r, 0x3f), door(R.r, 0x40)), flush=True)
    assert R.r.w(ROOM) == 23
    to_room24(R); item455(R); cross(R)
    print('end: room %d pos %s health %d xp %d ruck count %d' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), type8(R.r)['count']), flush=True)
    R.r.close()


if __name__ == '__main__':
    main()
