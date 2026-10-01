"""route_to_room33.py: natural joystick/keyboard input only.  Room 16 (the end of route_to_room16.py) -> door `$1d` -> room 30 (holy water 213 drunk through its icon 9: health 33 -> 35)
-> the south gap at x lead 36 -> room 31 -> 32 -> back to 31's west side -> room 33 (the regalia room, `$21`), arriving at (20,47,14,41) with health 35 and nothing injected.

    cd M68000 && .venv/bin/python reversing/cadaver/py/secrets/overlay/action/route_to_room33.py     (about 3 min; needs scratchpad/.../r16/ck_e_room16.snap)

Then the regalia walk and the BUTTON from that arrival, still without a poke or an injected entry (about 10 min):

    RW_DIR=rwn RW_START=$PWD/scratchpad/cadaver/secrets_out/action/r16/ck_h_room33.snap .venv/bin/python reversing/cadaver/py/secrets/overlay/action/regalia_walk.py full

Why this route: health only ever goes down by a verb 45 with a negative word, and the only ways up are the restoratives of `secrets.md` (water 213/214 +2 each in room 30, 392 +10 in room 46, 135 +2 in room 45) and the
level start; room 16 has 33 of 100.  The room-15 and room-30 hazards (objects 902/904 and 443-class touches, creature 237) cost 5 to 30 health per crossing, so the leg choices below are the ones that lost none
(a breadth-first search over holds pruned on any health loss, `trek`'s node semantics).  Checkpoints go to scratchpad/cadaver/secrets_out/action/r16/ck_g_*.snap and ck_h_*.snap.
Like route_to_room16.py it reloads (snapshot, close, reopen) after each hold the way the search did: `Repl.__init__` runs `s 1` and a hold's outcome depends on that phase."""
import sys, os
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from route_lib import *


def snap_reopen(r, name):
    path = SN + 'ck_%s.snap' % name
    r.snap(path); r.close()
    r = Repl(path)
    return r, Tally(r)


def main():
    r = Repl(SN + 'ck_e_room16.snap'); t = Tally(r)
    xp0 = r.l(A5 + 1192)
    print('start: room %d pos %s health %d xp %d' % (r.w(ROOM), pos(r), r.w(HEALTH), xp0), flush=True)
    assert r.w(ROOM) == 16
    room, p = hold(r, LEFT); print('   L ->', room, p); assert room == 30           # door $1d, arrival (55,20,49,14)
    r.cmd('s 100000')
    room, p = hold(r, LEFT); print('   L ->', room, p)                              # stall against the holy water 213
    ck(r, 'g_at213')
    res = probe(r); print('   probe', res and (res[0], res[1])); assert res and res[0] == 213 and 9 in res[1]
    h0 = r.w(HEALTH); t.reset(); open_panel(r, t); pick_icon_id(r, t, 9); t.run(100000, sites=[0xa5c0, 0xa5d2, 0xfe24, 0x10cc8])
    print('   drink: health', h0, '->', r.w(HEALTH), 'hits', t.show()); assert r.w(HEALTH) == h0 + 2
    r, t = snap_reopen(r, 'g_water1')
    hold(r, DOWN)                                                                    # to the south wall at x 23..29
    print('   right', goto(r, RIGHT, lambda p: p[0] >= 36))                         # the gap in the south wall is at x 31..37 and beyond (portal 1: x 28..51)
    room, p = hold(r, DOWN); print('   D ->', room, p); assert room == 31
    r.cmd('s 100000')
    r, t = snap_reopen(r, 'g_room31')
    for mv in 'LDLU':                                                                # 32 (door $2c), the south wall of 32, back west, then up through door $2d
        room, p = hold(r, K[mv]); print('   %s -> room %2d %s health %d' % (mv, room, p, r.w(HEALTH)), flush=True)
        r, t = snap_reopen(r, 'g_hop_%s' % mv)
    assert r.w(ROOM) == 33
    r.cmd('s 100000'); dump(r, 'room 33 (natural arrival)'); ck(r, 'h_room33')
    print('arrived: room %d pos %s health %d xp %d' % (r.w(ROOM), pos(r), r.w(HEALTH), r.l(A5 + 1192)))
    r.close()


K = {'U': UP, 'D': DOWN, 'L': LEFT, 'R': RIGHT}


def ck(r, name): r.snap(SN + 'ck_%s.snap' % name)


if __name__ == '__main__':
    main()
