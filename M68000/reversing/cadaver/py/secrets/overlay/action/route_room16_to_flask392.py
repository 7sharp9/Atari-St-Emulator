"""route_room16_to_flask392.py: natural joystick input only, nothing poked.  Room 16 -> 17 -> 38 -> 39 -> 40 -> 42 -> 46, take the scented oil 182 that blocks the flask, drink flask 392 (verb 45: +10 health).

    cd M68000 && .venv/bin/python <this file> OUTDIR [START SNAP] [--forward-only]

OUTDIR gets the checkpoint snapshots (ck_NN_*.snap) and nothing else is written.  Default start: scratchpad/cadaver/secrets_out/action/r16/ck_e_room16.snap (room 16, health 33).
Every hold starts from a reopened snapshot (`Repl.__init__` runs `s 1`, a hold's outcome depends on that phase: trek's node semantics)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from route_chain import *


def forward(R):
    R.S('settle16', 20000)
    if pos(R.r) != (20, 13, 14, 7):             # arrival from room 30 (the treasury road) is at (13,20,7,14): R stalls at x 66..72, U to the north wall, then R
        R.H('R_stall', 'R', 16)
        R.H('U_north', 'U', 16)
    R.H('R', 'R', 17)
    R.S('settle17', 100000)
    R.G('goto_R40', 'R', lambda p: p[0] >= 40)
    R.H('D', 'D', 38)
    R.S('settle38', 100000)
    R.H('D', 'D')
    R.G('goto_L22', 'L', lambda p: p[0] <= 22)
    R.H('D', 'D', 39)
    R.S('settle39', 100000)
    R.G('goto_R46', 'R', lambda p: p[0] >= 46)
    R.H('D', 'D')
    R.H('D', 'D', 40)
    R.S('settle40', 100000)
    for mv in 'DLRD': R.H(mv, mv)
    assert R.r.w(ROOM) == 42
    R.S('settle42', 100000)
    for mv in 'DRLD': R.H(mv, mv)
    assert R.r.w(ROOM) == 46
    R.S('settle46', 100000)
    R.H('D', 'D')
    R.G('goto_L12', 'L', lambda p: p[0] <= 12)
    R.H('D_oil', 'D')

    def take_oil(r):                          # scented oil 182 blocks the flask: icon 2 takes it
        res = probe(r); assert res and res[0] == 182, res
        t = Tally(r); open_panel(r, t); ic = icons(r); pick_icon_id(r, t, 2); t.run(100000)
        return 'probe %s icons %s ruck %s' % (res[:2], ic, type8(r)['recs'][:type8(r)['count'] + 2])
    R.leg('take182', take_oil)
    R.H('D_flask', 'D')

    def drink(r):
        res = probe(r); assert res and res[0] == 392, res
        t = Tally(r); h0 = r.w(HEALTH); open_panel(r, t); ic = icons(r); pick_icon_id(r, t, 9); t.run(100000, sites=[0xa5c0, 0xa5d2, 0xfe24, 0x10cc8])
        assert r.w(HEALTH) == h0 + 10, (h0, r.w(HEALTH))
        return 'probe %s icons %s hits %s' % (res[:2], ic, t.show())
    R.leg('drink392', drink)


def back(R):
    """flask 392 stall in room 46 -> room 16 (the legs were found by health-pruned searches over holds, 86th-87th pass; health 43 on every one)"""
    assert R.r.w(ROOM) == 46
    sc = R.settle_on_change
    sc('U', lambda r: hold(r, UP), 42)
    sc('goto_R66', lambda r: goto(r, RIGHT, lambda p: p[0] >= 66))
    sc('U', lambda r: hold(r, UP), 40)
    sc('U', lambda r: hold(r, UP))
    sc('goto_L47', lambda r: goto(r, LEFT, lambda p: p[0] <= 47))
    sc('U', lambda r: hold(r, UP), 39)
    sc('U', lambda r: hold(r, UP))
    sc('goto_L22', lambda r: goto(r, LEFT, lambda p: p[0] <= 22))
    sc('U', lambda r: hold(r, UP), 38)
    sc('U', lambda r: hold(r, UP))
    sc('goto_R44', lambda r: goto(r, RIGHT, lambda p: p[0] >= 44))
    sc('U', lambda r: hold(r, UP), 17)
    sc('L', lambda r: hold(r, LEFT), 16)
    sc('U', lambda r: hold(r, UP))               # room 16 (79,20,73,14) -> north wall (79,12,73,6)
    sc('goto_L20', lambda r: goto(r, LEFT, lambda p: p[0] <= 20))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    out = a[0]; start = a[1] if len(a) > 1 else OUT + 'r16/ck_e_room16.snap'
    R = Route(out, start)
    print('start: room %d pos %s health %d xp %d ruck %s' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), type8(R.r)['count']), flush=True)
    forward(R)
    if '--forward-only' not in sys.argv: back(R)
    print('end: room %d pos %s health %d xp %d ruck count %d' % (R.r.w(ROOM), pos(R.r), R.r.w(HEALTH), R.r.l(A5 + 1192), type8(R.r)['count']), flush=True)
    R.r.close()


if __name__ == '__main__':
    main()
