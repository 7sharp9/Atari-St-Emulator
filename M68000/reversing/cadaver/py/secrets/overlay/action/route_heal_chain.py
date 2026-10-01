"""route_heal_chain.py: natural joystick/keyboard input only, nothing poked.  The treasury (room 37, crown 53 and key 104 carried, health 35) -> room 16 (LEVER 86, rooms 34, 32, 33, 32, 31, 30: water 214, +2) ->
the heal road (rooms 17, 38, 39, 40, 42, 46: scented oil 182 taken, flask 392 drunk, +10) -> back to room 16 -> room 15 (wait 2.3M steps for the patrol of 902) -> 13 -> 14 -> BUTTONs 183, 181, 180, 179 ->
the stall under door $2a in room 13.  Same legs as route_treasury_to_room16.py, route_room16_to_flask392.py and route_room16_to_door2a.py, with the reload after every leg.

    cd M68000 && .venv/bin/python <this file> OUTDIR [START SNAP] [--no-heal]      (about 6 min; default start: scratchpad/cadaver/secrets_out/action/rwn2/taken53.snap)

--no-heal skips the room 17..46 trip (treasury -> room 16 -> door $2a as the promoted scripts chain it).  OUTDIR gets the checkpoint snapshots and nothing else is written."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_chain import *
import route_room16_to_flask392 as heal

SITES = [0xa43c, 0xa486, 0xfe24, 0xfe5a, 0x10cc8, 0x104e2, 0x10514]


def treasury(R):
    assert R.r.w(ROOM) == 37
    R.H('L_lever', 'L')

    def lever(r):
        t = Tally(r); open_panel(r, t); ic = icons(r); pick_icon_id(r, t, 7); r.cmd('s 300000')
        assert ic == [7, 11, 6], ic; assert r.w(ROOM) == 34
        return 'icons %s -> room 34' % ic
    R.leg('lever_icon7', lever)
    for mv, want in [('R', 32), ('U', 33), ('D', 32), ('R', 31), ('R', 31), ('U', 30)]:
        R.H(mv, mv, want)
    R.G('goto_L34', 'L', lambda p: p[0] <= 34)
    R.H('U_stall', 'U')

    def drink(r):
        t = Tally(r); h0 = r.w(HEALTH); open_panel(r, t); ic = icons(r)
        pick_icon_id(r, t, 9); t.run(100000, sites=[0xa5c0, 0xa5d2, 0xfe24, 0x10cc8])
        assert r.w(HEALTH) == h0 + 2, (h0, r.w(HEALTH)); return 'icons %s, icon 9 hits %s' % (ic, t.show())
    R.leg('drink214', drink)
    R.H('R_to_16', 'R', 16)


def press(r, oid, icon=4):
    hold(r, UP)
    res = probe(r); assert res and res[0] == oid, res
    t = Tally(r); open_panel(r, t); pick_icon_id(r, t, icon); t.run(100000, sites=SITES)
    return 'pressed %s hits %s door2a %s' % (oid, t.show(), door(r, 0x2a))


def door2a(R):
    def climb(r):
        room, p = hold(r, UP); r.cmd('s 150000'); return None
    R.leg('U_16_to_15', climb, 15)
    R.S('wait_2.3M', 2300000)
    R.leg('U_15_to_13', lambda r: (hold(r, UP, max_steps=5000000), r.cmd('s 150000'))[0], 13)
    R.leg('R_13_to_14', lambda r: (hold(r, RIGHT), r.cmd('s 150000'))[0], 14)

    def b183(r): hold(r, UP); return press(r, 183)
    R.leg('button183', b183)
    R.leg('button181', lambda r: (goto(r, RIGHT, lambda p: p[0] >= 48), press(r, 181))[1])
    R.leg('button180', lambda r: (goto(r, LEFT, lambda p: p[0] <= 38), press(r, 180))[1])
    R.leg('button179', lambda r: (goto(r, LEFT, lambda p: p[0] <= 25), press(r, 179))[1])
    assert door(R.r, 0x2a)[4:8] == '0000', door(R.r, 0x2a)
    R.H('D_14', 'D')
    R.leg('L_14_to_13', lambda r: (hold(r, LEFT), r.cmd('s 150000'))[0], 13)
    R.H('U_13', 'U')
    R.leg('L_stall_2a', lambda r: (hold(r, LEFT), r.cmd('s 30000'))[0])


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    out = a[0]; start = a[1] if len(a) > 1 else OUT + 'rwn2/taken53.snap'
    R = Route(out, start)
    rk = lambda: 'ruck count %d recs %s' % (type8(R.r)['count'], type8(R.r)['recs'][:type8(R.r)['count'] + 1])
    print('start: room %d pos %s health %d xp %d %s' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), rk()), flush=True)
    treasury(R)
    print('--- room 16: health %d %s' % (R.r.w(HEALTH), rk()), flush=True)
    if '--no-heal' not in sys.argv:
        heal.forward(R); heal.back(R)
        print('--- back in room 16: health %d %s' % (R.r.w(HEALTH), rk()), flush=True)
    door2a(R)
    print('end: room %d pos %s health %d xp %d door $2a %s %s' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), door(R.r, 0x2a), rk()), flush=True)
    R.r.close()


if __name__ == '__main__':
    main()
